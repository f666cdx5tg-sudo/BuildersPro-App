import SwiftUI
import SwiftData
import PhotosUI

struct PhotosView: View {
    @Environment(\.modelContext) private var context
    let job: Job
    let space: Space?              // nil = Unfiled
    @State private var picked: [PhotosPickerItem] = []
    @State private var selecting = false
    @State private var selection = Set<PersistentIdentifier>()
    @State private var openPhoto: SitePhoto?
    @State private var camera = false

    private var photos: [SitePhoto] {
        (job.photos ?? []).filter { $0.space?.uid == space?.uid }.sorted { $0.created > $1.created }
    }
    private let cols = [GridItem(.adaptive(minimum: 100), spacing: 4)]

    var body: some View {
        ScrollView {
            LazyVGrid(columns: cols, spacing: 4) {
                ForEach(photos) { p in
                    PhotoThumb(photo: p)
                        .overlay(alignment: .topTrailing) {
                            if selecting {
                                Image(systemName: selection.contains(p.persistentModelID) ? "checkmark.circle.fill" : "circle")
                                    .padding(6).foregroundStyle(.white, .blue)
                            }
                        }
                        .onTapGesture {
                            guard selecting else { openPhoto = p; return }
                            if !selection.insert(p.persistentModelID).inserted { selection.remove(p.persistentModelID) }
                        }
                }
            }.padding(4)
        }
        .navigationTitle(space?.name ?? "Unfiled")
        .toolbar {
            // one button holds the options (standing rule)
            Menu {
                PhotosPicker(selection: $picked, matching: .images) { Label("Add photos", systemImage: "plus") }
                #if os(iOS)
                if CameraPicker.available { Button("Take a photo", systemImage: "camera") { camera = true } }
                #endif
                Button(selecting ? "Done selecting" : "Select", systemImage: "checkmark.circle") {
                    selecting.toggle(); selection.removeAll()
                }
                if selecting && !selection.isEmpty {
                    Menu("Assign to space", systemImage: "folder") {
                        ForEach((job.spaces ?? []).sorted { $0.name < $1.name }) { s in
                            Button(s.name) { assign(to: s) }
                        }
                    }
                    Button("Delete selected", systemImage: "trash", role: .destructive) { deleteSelected() }
                }
            } label: { Image(systemName: "line.3.horizontal") }
        }
        .onChange(of: picked) { _, items in Task { await load(items) } }
        .navigationDestination(item: $openPhoto) { p in PhotoViewer(photo: p) }
        #if os(iOS)
        .fullScreenCover(isPresented: $camera) {
            CameraPicker { data in
                let p = SitePhoto(data: data); p.job = job; p.space = space
                context.insert(p)
            }.ignoresSafeArea()
        }
        #endif
    }

    private func load(_ items: [PhotosPickerItem]) async {
        for it in items {
            if let data = try? await it.loadTransferable(type: Data.self) {
                let p = SitePhoto(data: data); p.job = job; p.space = space
                context.insert(p)
            }
        }
        picked = []
    }
    private func assign(to s: Space) {
        photos.filter { selection.contains($0.persistentModelID) }.forEach { $0.space = s }
        selection.removeAll(); selecting = false
    }
    private func deleteSelected() {
        photos.filter { selection.contains($0.persistentModelID) }.forEach { context.delete($0) }
        selection.removeAll(); selecting = false
    }
}

struct PhotoThumb: View {
    let photo: SitePhoto
    var body: some View {
        Group {
            if let d = photo.data, let img = Self.image(d) {
                img.resizable().scaledToFill()
            } else { Color.gray.opacity(0.3) }
        }
        .frame(minHeight: 100).aspectRatio(1, contentMode: .fit).clipped()
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
    static func image(_ d: Data) -> Image? {
        #if canImport(UIKit)
        UIImage(data: d).map { Image(uiImage: $0) }
        #else
        NSImage(data: d).map { Image(nsImage: $0) }
        #endif
    }
}


// MARK: - Viewer, markup, camera

struct PhotoViewer: View {
    @Bindable var photo: SitePhoto
    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                if let d = photo.data, let img = PhotoThumb.image(d) { img.resizable().scaledToFit() }
                TextField("Caption", text: $photo.caption).textFieldStyle(.roundedBorder).padding(.horizontal)
                if let d = photo.data {
                    NavigationLink { MarkupView(data: d) { photo.data = $0 } } label: {
                        Label("Mark up (draw on photo)", systemImage: "pencil.tip.crop.circle")
                    }
                }
            }.padding(.vertical)
        }
        .navigationTitle("Photo")
    }
}

struct Stroke: Identifiable {
    let id = UUID()
    var points: [CGPoint]            // 0...1 of the picture's width/height
    var color: Color
}

/// Draw on a photo with a finger or mouse; Save puts the marked-up picture back in place of the original.
struct MarkupView: View {
    let data: Data
    let onSave: (Data) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var strokes: [Stroke] = []
    @State private var color: Color = .red
    private let palette: [Color] = [.red, .yellow, .blue, .green, .white, .black]

    var body: some View {
        VStack(spacing: 12) {
            if let img = PhotoThumb.image(data) {
                img.resizable().scaledToFit()
                    .overlay {
                        GeometryReader { g in
                            Canvas { ctx, size in MarkupView.draw(strokes, in: &ctx, size: size) }
                                .gesture(DragGesture(minimumDistance: 0).onChanged { v in
                                    let pt = CGPoint(x: min(max(v.location.x / g.size.width, 0), 1),
                                                     y: min(max(v.location.y / g.size.height, 0), 1))
                                    if v.translation == .zero { strokes.append(Stroke(points: [pt], color: color)) }
                                    else if !strokes.isEmpty { strokes[strokes.count - 1].points.append(pt) }
                                })
                        }
                    }
                    .padding(.horizontal)
            }
            HStack(spacing: 14) {
                ForEach(palette, id: \.self) { c in
                    Circle().fill(c).frame(width: 30, height: 30)
                        .overlay(Circle().stroke(Color.primary, lineWidth: color == c ? 3 : 0.5))
                        .onTapGesture { color = c }
                }
                Spacer()
                Button("Undo", systemImage: "arrow.uturn.backward") { _ = strokes.popLast() }.disabled(strokes.isEmpty)
            }.padding(.horizontal)
            HStack {
                Button("Cancel", role: .cancel) { dismiss() }
                Spacer()
                Button("Save") { save() }.buttonStyle(.borderedProminent).disabled(strokes.isEmpty)
            }.padding(.horizontal).padding(.bottom)
        }
        .navigationTitle("Mark up")
    }

    static func draw(_ strokes: [Stroke], in ctx: inout GraphicsContext, size: CGSize) {
        let w = max(3, min(size.width, size.height) * 0.008)
        for s in strokes {
            var path = Path()
            for (i, p) in s.points.enumerated() {
                let q = CGPoint(x: p.x * size.width, y: p.y * size.height)
                if i == 0 { path.move(to: q) } else { path.addLine(to: q) }
            }
            if s.points.count == 1, let p = s.points.first {
                let q = CGPoint(x: p.x * size.width, y: p.y * size.height)
                ctx.fill(Path(ellipseIn: CGRect(x: q.x - w / 2, y: q.y - w / 2, width: w, height: w)), with: .color(s.color))
            } else {
                ctx.stroke(path, with: .color(s.color), style: StrokeStyle(lineWidth: w, lineCap: .round, lineJoin: .round))
            }
        }
    }

    @MainActor private func save() {
        guard let img = PhotoThumb.image(data), let px = PhotoThumb.pixelSize(data) else { return }
        let k = min(1, 2000 / max(px.width, px.height))
        let size = CGSize(width: px.width * k, height: px.height * k)
        let marked = strokes
        let view = ZStack {
            img.resizable().frame(width: size.width, height: size.height)
            Canvas { ctx, sz in MarkupView.draw(marked, in: &ctx, size: sz) }.frame(width: size.width, height: size.height)
        }.frame(width: size.width, height: size.height)
        let r = ImageRenderer(content: view)
        r.scale = 1
        #if canImport(UIKit)
        if let out = r.uiImage?.jpegData(compressionQuality: 0.85) { onSave(out); dismiss() }
        #else
        if let ns = r.nsImage, let tiff = ns.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
           let out = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.85]) { onSave(out); dismiss() }
        #endif
    }
}

extension PhotoThumb {
    static func pixelSize(_ d: Data) -> CGSize? {
        #if canImport(UIKit)
        UIImage(data: d).map { CGSize(width: $0.size.width * $0.scale, height: $0.size.height * $0.scale) }
        #else
        NSImage(data: d).map { $0.size }
        #endif
    }
}

#if os(iOS)
import UIKit
struct CameraPicker: UIViewControllerRepresentable {
    static var available: Bool { UIImagePickerController.isSourceTypeAvailable(.camera) }
    let onImage: (Data) -> Void
    @Environment(\.dismiss) private var dismiss

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let c = UIImagePickerController()
        c.sourceType = CameraPicker.available ? .camera : .photoLibrary
        c.delegate = context.coordinator
        return c
    }
    func updateUIViewController(_ vc: UIImagePickerController, context: Context) {}
    func makeCoordinator() -> Coord { Coord(self) }

    final class Coord: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: CameraPicker
        init(_ p: CameraPicker) { parent = p }
        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            if let img = info[.originalImage] as? UIImage, let d = img.jpegData(compressionQuality: 0.85) { parent.onImage(d) }
            parent.dismiss()
        }
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) { parent.dismiss() }
    }
}
#endif
