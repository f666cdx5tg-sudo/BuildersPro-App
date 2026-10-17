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
        .navigationDestination(item: $openPhoto) { p in
            MarkupView(data: p.data ?? Data(), caption: Binding(get: { p.caption }, set: { p.caption = $0 })) { p.data = $0 }
        }
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
        Color.gray.opacity(0.3)
            .aspectRatio(1, contentMode: .fit)          // square cell, never taller/wider than its slot
            .overlay {
                if let d = photo.data, let img = Self.small(d, 500) {
                    img.resizable().scaledToFill()
                }
            }
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

enum MarkTool: String, CaseIterable, Identifiable {
    case pen = "Pen", text = "Text", circle = "Circle", arrow = "Arrow", square = "Square"
    var id: String { rawValue }
    var symbol: String {
        switch self {
        case .pen: return "pencil.tip"
        case .text: return "textformat"
        case .circle: return "circle"
        case .arrow: return "arrow.up.right"
        case .square: return "square"
        }
    }
}

struct Stroke: Identifiable {
    let id = UUID()
    var tool: MarkTool = .pen
    var points: [CGPoint]            // 0...1 of the picture's width/height
    var text: String = ""
    var color: Color
    var width: CGFloat               // fraction of the picture's short side
}

/// Opens straight into drawing: tools sit on a bar above the photo, so they are always visible.
struct MarkupView: View {
    let data: Data
    var caption: Binding<String>? = nil
    let onSave: (Data) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var strokes: [Stroke] = []
    @State private var color: Color = .red
    @State private var width: CGFloat = 0.008
    @State private var tool: MarkTool = .pen
    @State private var didMove = false
    @State private var moveActive = false
    @State private var movingIndex: Int?
    @State private var lastPoint: CGPoint = .zero
    @State private var textSpot: CGPoint?
    @State private var textValue = ""
    private let palette: [Color] = [.red, .yellow, .blue, .green, .white, .black]
    private let widths: [(String, CGFloat)] = [("Thin", 0.004), ("Medium", 0.008), ("Thick", 0.016)]

    var body: some View {
        VStack(spacing: 10) {
            if let img = PhotoThumb.image(data) {
                img.resizable().scaledToFit()
                    .overlay {
                        GeometryReader { g in
                            Canvas { ctx, size in MarkupView.draw(strokes, in: &ctx, size: size) }
                                .gesture(DragGesture(minimumDistance: 0).onChanged { v in
                                    let pt = CGPoint(x: min(max(v.location.x / g.size.width, 0), 1),
                                                     y: min(max(v.location.y / g.size.height, 0), 1))
                                    if !moveActive {
                                        moveActive = true
                                        didMove = false
                                        movingIndex = MarkupView.hit(strokes, at: v.location, size: g.size)
                                        lastPoint = pt
                                        if movingIndex == nil && tool != .text {
                                            strokes.append(Stroke(tool: tool, points: [pt], color: color, width: width))
                                        }
                                        return
                                    }
                                    if v.translation != .zero { didMove = true }
                                    if let i = movingIndex, strokes.indices.contains(i) {
                                        let dx = pt.x - lastPoint.x, dy = pt.y - lastPoint.y
                                        strokes[i].points = strokes[i].points.map { CGPoint(x: $0.x + dx, y: $0.y + dy) }
                                        lastPoint = pt
                                    } else if tool != .text, !strokes.isEmpty {
                                        if tool == .pen { strokes[strokes.count - 1].points.append(pt) }
                                        else { strokes[strokes.count - 1].points = [strokes[strokes.count - 1].points[0], pt] }
                                    }
                                }.onEnded { v in
                                    let hitSomething = movingIndex != nil
                                    let moved = didMove
                                    moveActive = false; movingIndex = nil
                                    if tool == .text && !hitSomething && !moved {
                                        textSpot = CGPoint(x: min(max(v.location.x / g.size.width, 0), 1),
                                                           y: min(max(v.location.y / g.size.height, 0), 1))
                                        textValue = ""
                                    }
                                })
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .padding(.horizontal, 8)
            }
            if let caption { TextField("Caption", text: caption).textFieldStyle(.roundedBorder).padding(.horizontal) }
        }
        .padding(.bottom, 8)
        .navigationTitle("Mark up")
        .toolbar { markupBar }
        .alert("Add text", isPresented: Binding(get: { textSpot != nil }, set: { if !$0 { textSpot = nil } })) {
            TextField("Type here", text: $textValue)
            Button("Add") {
                let t = textValue.trimmingCharacters(in: .whitespacesAndNewlines)
                if let spot = textSpot, !t.isEmpty {
                    strokes.append(Stroke(tool: .text, points: [spot], text: t, color: color, width: width))
                }
                textSpot = nil
            }
            Button("Cancel", role: .cancel) { textSpot = nil }
        }
    }

    private let colorNames = ["Red", "Yellow", "Blue", "Green", "White", "Black"]

    @ToolbarContentBuilder private var markupBar: some ToolbarContent {
        ToolbarItemGroup(placement: .primaryAction) {
            Image(systemName: tool.symbol)
            Circle().fill(color).frame(width: 20, height: 20).overlay(Circle().stroke(Color.gray.opacity(0.6), lineWidth: 1))
            Menu {
                Picker("Tool", selection: $tool) {
                    ForEach(MarkTool.allCases) { t in Label(t.rawValue, systemImage: t.symbol).tag(t) }
                }
                Picker("Color", selection: $color) {
                    ForEach(Array(palette.enumerated()), id: \.offset) { i, c in Label(colorNames[i], systemImage: "circle.fill").tint(c).tag(c) }
                }
                Picker("Size", selection: $width) {
                    ForEach(widths, id: \.0) { w in Text(w.0).tag(w.1) }
                }
                Divider()
                Button { _ = strokes.popLast() } label: { Label("Undo", systemImage: "arrow.uturn.backward") }.disabled(strokes.isEmpty)
                Button(role: .destructive) { strokes.removeAll() } label: { Label("Clear", systemImage: "trash") }.disabled(strokes.isEmpty)
            } label: { Image(systemName: "line.3.horizontal") }
            Button("Save") { save() }.fontWeight(.bold).disabled(strokes.isEmpty)
        }
    }

    /// Which mark is under this point (topmost first)? Used by the Move tool.
    static func hit(_ strokes: [Stroke], at p: CGPoint, size: CGSize) -> Int? {
        let tol: CGFloat = 24
        func px(_ q: CGPoint) -> CGPoint { CGPoint(x: q.x * size.width, y: q.y * size.height) }
        func dist(_ p: CGPoint, _ a: CGPoint, _ b: CGPoint) -> CGFloat {
            let dx = b.x - a.x, dy = b.y - a.y
            let l2 = dx * dx + dy * dy
            if l2 == 0 { return hypot(p.x - a.x, p.y - a.y) }
            let t = max(0, min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2))
            return hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))
        }
        for i in strokes.indices.reversed() {
            let s = strokes[i]
            let pts = s.points.map(px)
            guard let a = pts.first else { continue }
            switch s.tool {
            case .pen, .arrow:
                if pts.count == 1 { if hypot(p.x - a.x, p.y - a.y) < tol { return i } }
                for k in 1..<max(pts.count, 1) where dist(p, pts[k - 1], pts[k]) < tol { return i }
            case .circle, .square:
                guard let b = pts.last else { continue }
                let r = CGRect(x: min(a.x, b.x), y: min(a.y, b.y), width: abs(b.x - a.x), height: abs(b.y - a.y)).insetBy(dx: -tol, dy: -tol)
                if r.contains(p) { return i }
            case .text:
                let fs = max(14, min(size.width, size.height) * s.width * 4)
                let r = CGRect(x: a.x, y: a.y, width: CGFloat(s.text.count) * fs * 0.62, height: fs * 1.3).insetBy(dx: -tol / 2, dy: -tol / 2)
                if r.contains(p) { return i }
            }
        }
        return nil
    }

    static func draw(_ strokes: [Stroke], in ctx: inout GraphicsContext, size: CGSize) {
        for s in strokes {
            let w = max(3, min(size.width, size.height) * s.width)
            let pts = s.points.map { CGPoint(x: $0.x * size.width, y: $0.y * size.height) }
            guard let a = pts.first else { continue }
            let style = StrokeStyle(lineWidth: w, lineCap: .round, lineJoin: .round)
            switch s.tool {
            case .pen:
                if pts.count == 1 {
                    ctx.fill(Path(ellipseIn: CGRect(x: a.x - w / 2, y: a.y - w / 2, width: w, height: w)), with: .color(s.color))
                } else {
                    var path = Path(); path.move(to: a)
                    for q in pts.dropFirst() { path.addLine(to: q) }
                    ctx.stroke(path, with: .color(s.color), style: style)
                }
            case .text:
                let fs = max(14, min(size.width, size.height) * s.width * 4)
                let resolved = ctx.resolve(Text(s.text).font(.system(size: fs, weight: .bold)).foregroundColor(s.color))
                let box = resolved.measure(in: CGSize(width: size.width * 0.9, height: size.height))
                let origin = CGPoint(x: min(a.x, max(0, size.width - box.width)), y: min(a.y, max(0, size.height - box.height)))
                ctx.drawLayer { layer in
                    layer.addFilter(.shadow(color: .black.opacity(0.7), radius: 2, x: 0, y: 1))
                    layer.draw(resolved, at: origin, anchor: .topLeading)
                }
            case .circle, .square:
                guard pts.count > 1, let b = pts.last else { continue }
                let r = CGRect(x: min(a.x, b.x), y: min(a.y, b.y), width: abs(b.x - a.x), height: abs(b.y - a.y))
                ctx.stroke(s.tool == .circle ? Path(ellipseIn: r) : Path(r), with: .color(s.color), style: style)
            case .arrow:
                guard pts.count > 1, let b = pts.last else { continue }
                var path = Path(); path.move(to: a); path.addLine(to: b)
                let ang = atan2(b.y - a.y, b.x - a.x)
                let head = max(14, w * 5)
                for d in [CGFloat.pi * 0.85, -CGFloat.pi * 0.85] {
                    path.move(to: b)
                    path.addLine(to: CGPoint(x: b.x + cos(ang + d) * head, y: b.y + sin(ang + d) * head))
                }
                ctx.stroke(path, with: .color(s.color), style: style)
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

import ImageIO
import UniformTypeIdentifiers
extension PhotoThumb {
    /// Bakes EXIF orientation into the pixels (and caps size) so every screen and the markup canvas agree on "up".
    static func upright(_ d: Data) -> Data {
        guard let src = CGImageSourceCreateWithData(d as CFData, nil) else { return d }
        let props = CGImageSourceCopyPropertiesAtIndex(src, 0, nil) as? [CFString: Any]
        let orient = (props?[kCGImagePropertyOrientation] as? Int) ?? 1
        let w = (props?[kCGImagePropertyPixelWidth] as? Int) ?? 0, h = (props?[kCGImagePropertyPixelHeight] as? Int) ?? 0
        if orient == 1 && max(w, h) <= 3000 { return d }
        let o: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceCreateThumbnailWithTransform: true, kCGImageSourceThumbnailMaxPixelSize: 3000]
        guard let cg = CGImageSourceCreateThumbnailAtIndex(src, 0, o as CFDictionary) else { return d }
        let out = NSMutableData()
        guard let dest = CGImageDestinationCreateWithData(out, UTType.jpeg.identifier as CFString, 1, nil) else { return d }
        CGImageDestinationAddImage(dest, cg, [kCGImageDestinationLossyCompressionQuality: 0.85] as CFDictionary)
        return CGImageDestinationFinalize(dest) ? out as Data : d
    }
}

extension PhotoThumb {
    /// Downsampled decode — keeps memory low when many photos are on screen (full-size decode was getting the app killed).
    static func small(_ d: Data, _ maxPixels: CGFloat) -> Image? {
        guard let src = CGImageSourceCreateWithData(d as CFData, nil) else { return nil }
        let o: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceCreateThumbnailWithTransform: true, kCGImageSourceThumbnailMaxPixelSize: maxPixels]
        guard let cg = CGImageSourceCreateThumbnailAtIndex(src, 0, o as CFDictionary) else { return nil }
        return Image(decorative: cg, scale: 1)
    }
}
