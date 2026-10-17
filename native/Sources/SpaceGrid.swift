import SwiftUI
import ImageIO
import SwiftData
#if canImport(UIKit)
import UIKit
#else
import AppKit
#endif

/// Room icons: picked from the room's name, and every candidate is checked so a symbol this OS lacks never renders blank.
enum RoomIcon {
    static func exists(_ n: String) -> Bool {
        #if canImport(UIKit)
        return UIImage(systemName: n) != nil
        #else
        return NSImage(systemSymbolName: n, accessibilityDescription: nil) != nil
        #endif
    }
    static func first(_ names: [String]) -> String { names.first(where: exists) ?? "square.grid.2x2" }

    static func candidates(for name: String, stored: String) -> [String] {
        let l = name.lowercased()
        func has(_ w: String...) -> Bool { w.contains { l.contains($0) } }
        var c: [String] = []
        if has("kitchen") { c = ["fork.knife", "refrigerator", "cooktop"] }
        else if has("half bath", "powder", "toilet", "wc") { c = ["toilet", "bathtub", "drop"] }
        else if has("bath") { c = ["bathtub", "shower", "drop"] }
        else if has("bed") { c = ["bed.double", "moon"] }
        else if has("living", "family", "den", "lounge") { c = ["sofa", "tv"] }
        else if has("dining") { c = ["fork.knife", "chair.lounge"] }
        else if has("laundry", "washer", "utility") { c = ["washer", "tshirt", "drop"] }
        else if has("garage") { c = ["car", "door.garage.closed"] }
        else if has("office", "study") { c = ["desktopcomputer", "briefcase"] }
        else if has("stair") { c = ["figure.stairs", "stairs", "arrow.up.right"] }
        else if has("foyer", "entrance", "entry", "hall", "door") { c = ["door.left.hand.open", "door.left.hand.closed"] }
        else if has("boiler", "mechanical", "furnace", "heat", "hvac") { c = ["flame", "fanblades", "fan"] }
        else if has("attic") { c = ["triangle", "house"] }
        else if has("basement") { c = ["house.lodge", "arrow.down.to.line", "house"] }
        else if has("roof") { c = ["house", "triangle"] }
        else if has("chimney") { c = ["smoke", "flame"] }
        else if has("gutter", "downspout") { c = ["cloud.rain", "drop"] }
        else if has("driveway", "walk", "path") { c = ["road.lanes", "arrow.right"] }
        else if has("porch", "deck", "patio", "step", "ramp") { c = ["rectangle.split.3x1", "house"] }
        else if has("yard", "lawn", "garden", "fence") { c = ["leaf", "tree"] }
        else if has("window") { c = ["window.vertical.closed", "squareshape.split.2x2"] }
        else if has("closet", "storage") { c = ["archivebox", "shippingbox"] }
        if stored != "square.split.bottomrightquarter" { c.append(stored) }
        c.append("door.left.hand.closed")
        return c
    }
}

extension Space {
    /// The icon to show for this room.
    var icon: String { RoomIcon.first(RoomIcon.candidates(for: name, stored: symbol)) }
}

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
                if showExtras && mode == .photos && (job.photos ?? []).contains(where: { $0.space == nil }) { unfiledTile }
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
                SpaceIcon(name: space.name, symbol: space.symbol, size: 40)
                Spacer()
                PhotoStack(photos: space.photos ?? []).padding(.trailing, 52)
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

/// Little fanned stack of the newest photos for a space tile.
struct PhotoStack: View {
    let datas: [Data?]
    var thumb: CGFloat = 40
    init(photos: [SitePhoto], thumb: CGFloat = 40) { datas = photos.sorted { $0.created > $1.created }.map { $0.data }; self.thumb = thumb }
    init(datas: [Data?], thumb: CGFloat = 40) { self.datas = datas; self.thumb = thumb }
    var body: some View {
        let top = Array(datas.prefix(3))
        ZStack {
            ForEach(Array(top.enumerated().reversed()), id: \.offset) { i, p in
                Group {
                    if let d = p { ThumbImage(data: d, px: 120) }
                    else { Color.gray.opacity(0.4).overlay(Image(systemName: "photo").foregroundStyle(.secondary)) }
                }
                .frame(width: thumb, height: thumb).clipShape(RoundedRectangle(cornerRadius: 6))
                .overlay(RoundedRectangle(cornerRadius: 6).stroke(.white.opacity(0.85), lineWidth: 1.5))
                .rotationEffect(.degrees(Double(i) * 8 - 6)).offset(x: CGFloat(i) * 5, y: CGFloat(i) * -2)
            }
        }
        .frame(width: thumb + 12, height: thumb + 4)
        .opacity(top.isEmpty ? 0 : 1)
    }
    static func thumb(_ d: Data) -> Image? {
        guard let src = CGImageSourceCreateWithData(d as CFData, nil) else { return nil }
        let o: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceCreateThumbnailWithTransform: true, kCGImageSourceThumbnailMaxPixelSize: 120]
        guard let cg = CGImageSourceCreateThumbnailAtIndex(src, 0, o as CFDictionary) else { return nil }
        return Image(decorative: cg, scale: 1)
    }
}

// MARK: - Custom line drawings (same as the web app: steps, ramp, sidewalk, driveway)

enum LocGlyph {
    case stairs, ramp, walk, drive, water
    static func match(_ name: String) -> LocGlyph? {
        let n = name.lowercased()
        func has(_ p: String) -> Bool { n.range(of: p, options: .regularExpression) != nil }
        if has("\\bramps?\\b|handicap|wheelchair|\\bada\\b") { return .ramp }
        if has("\\bstairs?\\b|\\bsteps?\\b|\\bstoops?\\b|stairway|staircase") { return .stairs }
        if has("sidewalk|walkway|pathway|front walk") { return .walk }
        if has("water (service|line|main|meter)|\\bmeter\\b|\\bhose bib|spigot") { return .water }
        if has("driveway|\\bapron\\b|curb cut") { return .drive }
        return nil
    }
}

struct LocGlyphView: View {
    let glyph: LocGlyph
    var size: CGFloat = 30
    var body: some View {
        Canvas { ctx, sz in
            let vb: CGFloat = (glyph == .ramp || glyph == .water) ? 24 : 32
            let k = sz.width / vb
            func P(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * k, y: y * k) }
            func line(_ pts: [(CGFloat, CGFloat)], _ w: CGFloat) {
                var p = Path(); p.move(to: P(pts[0].0, pts[0].1))
                for q in pts.dropFirst() { p.addLine(to: P(q.0, q.1)) }
                ctx.stroke(p, with: .foreground, style: StrokeStyle(lineWidth: w * k, lineCap: .round, lineJoin: .round))
            }
            func dot(_ x: CGFloat, _ y: CGFloat, _ r: CGFloat, fill: Bool, w: CGFloat = 1.8) {
                let rect = CGRect(x: (x - r) * k, y: (y - r) * k, width: 2 * r * k, height: 2 * r * k)
                if fill { ctx.fill(Path(ellipseIn: rect), with: .foreground) }
                else { ctx.stroke(Path(ellipseIn: rect), with: .foreground, style: StrokeStyle(lineWidth: w * k)) }
            }
            switch glyph {
            case .stairs:
                line([(2,30),(8,30),(8,25),(14,25),(14,20),(20,20),(20,15),(26,15),(26,10),(30,10)], 1.8)
                line([(3,22.7),(28,1.9)], 1.8)
                for (x, y0, y1) in [(5.0,30.0,21.0),(11,25,16),(17,20,11),(23,15,6)] { line([(CGFloat(x),CGFloat(y0)),(CGFloat(x),CGFloat(y1))], 1.8) }
            case .ramp:
                var tri = Path(); tri.move(to: P(1.5,23)); tri.addLine(to: P(22.5,23)); tri.addLine(to: P(22.5,17.8)); tri.closeSubpath()
                ctx.fill(tri, with: .foreground)
                dot(10.6, 2.9, 1.9, fill: true)
                line([(10.2,6.3),(9.8,12.8),(14.9,12.8),(17.0,17.7)], 2.3)
                line([(10.1,9.2),(14.3,9.2)], 2.3)
                var arc: [(CGFloat, CGFloat)] = []
                var a: CGFloat = 16
                while a <= 248 { let r = a * .pi / 180; arc.append((8.88 + 4.4 * cos(r), 14.17 + 4.4 * sin(r))); a += 8 }
                line(arc, 2.3)
            case .walk:
                dot(17, 3.6, 1.9, fill: true)
                line([(11,22),(14.5,17)], 1.9)
                line([(20.5,22),(18,17),(14.5,13.5),(15.7,7)], 1.9)
                line([(10,14),(12.5,10.5),(17,9.3),(20.5,13),(24,14)], 1.9)
                line([(1.5,25.5),(30.5,25.5),(30.5,30),(1.5,30),(1.5,25.5)], 1.9)
                for x in [9.0, 16, 23] { line([(CGFloat(x),25.5),(CGFloat(x),30)], 1.9) }
            case .water:
                line([(2,12),(8,12)], 1.8); line([(16,12),(22,12)], 1.8)
                let box = Path(roundedRect: CGRect(x: 8 * k, y: 9 * k, width: 8 * k, height: 6 * k), cornerRadius: 1.5 * k)
                ctx.stroke(box, with: .foreground, style: StrokeStyle(lineWidth: 1.8 * k, lineJoin: .round))
                line([(12,9),(12,5)], 1.8); line([(9,5),(15,5)], 1.8)
                var d = Path(); d.move(to: P(12,18))
                d.addCurve(to: P(10.2,21), control1: P(10.8,19.6), control2: P(10.2,20.3))
                var a: CGFloat = 180
                while a >= 0 { let r = a * .pi / 180; d.addLine(to: P(12 + 1.8 * cos(r), 21 + 1.8 * sin(r))); a -= 10 }
                d.addCurve(to: P(12,18), control1: P(13.8,20.3), control2: P(13.2,19.6))
                ctx.stroke(d, with: .foreground, style: StrokeStyle(lineWidth: 1.8 * k, lineCap: .round, lineJoin: .round))
            case .drive:
                line([(1,29.5),(31,29.5)], 1.8)
                line([(18.5,29.5),(18.5,15.5),(24.5,10),(30.5,15.5),(30.5,29.5)], 1.8)
                line([(21,29.5),(21,20.5),(28,20.5),(28,29.5)], 1.8)
                line([(21,23.5),(28,23.5)], 1.8); line([(21,26.5),(28,26.5)], 1.8)
                line([(3.5,26),(2,26),(2,21.8),(4.8,17),(11.7,17),(15,21.8),(16.3,21.8),(16.3,26),(14.9,26)], 1.8)
                line([(7.4,26),(11.2,26)], 1.8); line([(4.3,21.8),(14.7,21.8)], 1.8)
                dot(5.5, 26.4, 1.9, fill: false); dot(13.1, 26.4, 1.9, fill: false)
            }
        }
        .frame(width: size, height: size)
    }
}

/// One icon for a space everywhere: the web app's drawings when the name calls for it, else an SF Symbol.
struct SpaceIcon: View {
    let name: String
    var symbol: String = ""
    var size: CGFloat = 30
    var body: some View {
        if let g = LocGlyph.match(name) { LocGlyphView(glyph: g, size: size) }
        else { Image(systemName: RoomIcon.first(RoomIcon.candidates(for: name, stored: symbol))).font(.system(size: size, weight: .semibold)) }
    }
}
