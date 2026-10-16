import SwiftUI
import SwiftData

/// One tile grid used by Spaces, Punch and Photos — grouped by level.
/// Press-and-hold a tile, drag it onto another tile or a level header to reorder / change level.
struct SpaceGrid: View {
    @Environment(\.modelContext) private var context
    let job: Job
    let mode: Section3
    var scroll = true
    var showExtras = true

    private var spaces: [Space] { job.spaces ?? [] }
    private var levels: [String] {
        Array(Set(spaces.map(\.level))).sorted { Levels.rank($0) < Levels.rank($1) }
    }
    private func inLevel(_ l: String) -> [Space] {
        spaces.filter { $0.level == l }.sorted { $0.order < $1.order }
    }
    private let cols = [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)]

    var body: some View {
        if scroll { ScrollView { content } } else { content }
    }

    private var content: some View {
            LazyVStack(alignment: .leading, spacing: 10, pinnedViews: []) {
                if showExtras && mode == .punch { generalTile }
                if showExtras && mode == .photos { unfiledTile }
                ForEach(levels, id: \.self) { level in
                    header(level)
                    LazyVGrid(columns: cols, spacing: 10) {
                        ForEach(inLevel(level)) { space in
                            NavigationLink { destination(space) } label: { SpaceTile(space: space, mode: mode) }
                                .buttonStyle(.plain)
                                .draggable(space.uid.uuidString)
                                .dropDestination(for: String.self) { ids, _ in
                                    move(ids.first, to: level, before: space)
                                }
                        }
                    }
                }
                if spaces.isEmpty {
                    ContentUnavailableView("No spaces yet", systemImage: "square.grid.2x2",
                                           description: Text("Use the ≡ button above to add one."))
                }
            }
            .padding(.horizontal, scroll ? 16 : 0).padding(.bottom, scroll ? 100 : 0)    // room so nothing hides behind buttons
    }

    private func header(_ level: String) -> some View {
        HStack {
            Text(Levels.title(level).uppercased()).font(.title3.weight(.heavy)).tracking(1).foregroundStyle(Theme.blue)
            Text("\(inLevel(level).count) areas").font(.title3.weight(.semibold)).foregroundStyle(.secondary)
            Spacer()
        }
        .padding(.top, 8)
        .overlay(alignment: .bottom) { Divider() }
        .dropDestination(for: String.self) { ids, _ in move(ids.first, to: level, before: nil) }
    }

    @ViewBuilder private func destination(_ s: Space) -> some View {
        switch mode {
        case .spaces, .punch: PunchListView(job: job, space: s)
        case .photos: PhotosView(job: job, space: s)
        }
    }

    private var generalTile: some View {
        let items = (job.punchItems ?? []).filter { $0.space == nil }
        return NavigationLink { PunchListView(job: job, space: nil) } label: {
            HStack {
                Image(systemName: "tray.full"); Text("General").font(.headline)
                Spacer()
                Text("\(items.filter { !$0.done }.count) open").foregroundStyle(.red).font(.subheadline.bold())
            }.padding().background(.quaternary, in: RoundedRectangle(cornerRadius: 14))
        }.buttonStyle(.plain)
    }

    private var unfiledTile: some View {
        let n = (job.photos ?? []).filter { $0.space == nil }.count
        return NavigationLink { PhotosView(job: job, space: nil) } label: {
            HStack {
                Image(systemName: "questionmark.folder"); Text("Unfiled").font(.headline)
                Spacer()
                Text("\(n) to file").foregroundStyle(.red).font(.subheadline.bold())
            }.padding().background(.quaternary, in: RoundedRectangle(cornerRadius: 14))
        }.buttonStyle(.plain)
    }

    /// Put the dragged space into `level`, just before `target` (or first in the level when target is nil).
    private func move(_ idString: String?, to level: String, before target: Space?) -> Bool {
        guard let idString, let id = UUID(uuidString: idString),
              let dragged = spaces.first(where: { $0.uid == id }), dragged.uid != target?.uid else { return false }
        let oldLevel = dragged.level
        dragged.level = level
        var group = inLevel(level).filter { $0.uid != dragged.uid }
        let at = target.flatMap { t in group.firstIndex(where: { $0.uid == t.uid }) } ?? 0
        group.insert(dragged, at: at)
        for (i, s) in group.enumerated() { s.order = i }
        if oldLevel != level { for (i, s) in inLevel(oldLevel).enumerated() { s.order = i } }
        return true
    }
}

struct SpaceTile: View {
    let space: Space
    let mode: Section3
    @AppStorage("bpDark") private var dark = true

    private var total: Int { space.openCount + space.doneCount }
    private var complete: Bool { total > 0 && space.openCount == 0 }
    private var pct: Double { total == 0 ? 0 : Double(space.doneCount) / Double(total) }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                Image(systemName: space.symbol).font(.system(size: 30))
                Spacer()
            }
            Text(space.name).font(.headline.weight(.heavy)).lineLimit(1).minimumScaleFactor(0.8)
            switch mode {
            case .spaces, .punch:
                HStack {
                    stat(space.openCount, "OPEN", .red)
                    Spacer()
                    stat(space.doneCount, "DONE", Theme.green)
                }
                Capsule().fill(Color.primary.opacity(0.12)).frame(height: 5)
                    .overlay(alignment: .leading) {
                        GeometryReader { g in Capsule().fill(complete ? Theme.green : Theme.blue).frame(width: g.size.width * pct) }
                    }
                HStack {
                    Text(total == 0 ? "No items" : "\(space.openCount) to do").font(.callout).foregroundStyle(.secondary)
                    Spacer()
                    Image(systemName: "camera").foregroundStyle(space.photoCount > 0 ? Theme.lightBlue : .secondary)
                    Text("\(space.photoCount)").font(.callout.weight(.bold)).foregroundStyle(space.photoCount > 0 ? Theme.lightBlue : .secondary)
                }
            case .photos:
                stat(space.photoCount, space.photoCount == 1 ? "PHOTO" : "PHOTOS", Theme.lightBlue)
            }
        }
        .padding(14).frame(minHeight: 150)
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 22))
        .overlay(alignment: .topTrailing) {
            Text(space.isExterior ? "EXT" : "INT").font(.system(size: 13, weight: .heavy)).foregroundStyle(space.isExterior ? Theme.orange : Theme.blue)
                .padding(.horizontal, 14).padding(.vertical, 5)
                .background((space.isExterior ? Theme.orange : Theme.blue).opacity(0.18), in: UnevenRoundedRectangle(bottomLeadingRadius: 14, topTrailingRadius: 22))
        }
        .overlay(RoundedRectangle(cornerRadius: 22).stroke(complete && mode != .photos ? Theme.green.opacity(0.7) : Theme.border(dark), lineWidth: 1.5))
        .contentShape(RoundedRectangle(cornerRadius: 22))
    }

    private func stat(_ n: Int, _ label: String, _ color: Color) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 5) {
            Text("\(n)").font(.system(size: 30, weight: .black)).foregroundStyle(n == 0 ? Color.secondary : color)
            Text(label).font(.subheadline.weight(.bold)).foregroundStyle(.secondary)
        }.lineLimit(1).minimumScaleFactor(0.7)
    }
}
