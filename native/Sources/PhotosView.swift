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
                            guard selecting else { return }
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
