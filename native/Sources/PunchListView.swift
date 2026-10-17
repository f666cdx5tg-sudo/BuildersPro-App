import SwiftUI
import SwiftData
import PhotosUI

struct PunchListView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @AppStorage("bpDark") private var dark = true
    let job: Job
    let space: Space?              // nil = General
    @State private var tradeFilter = ""
    @State private var status = "All"
    @State private var addOpen = false
    @State private var newText = ""
    @State private var newTrade = "Other"
    @State private var pick: [PhotosPickerItem] = []
    @State private var toDelete: PunchItem?
    @State private var renameOpen = false
    @State private var nameText = ""

    private var all: [PunchItem] { (job.punchItems ?? []).filter { $0.space?.uid == space?.uid }.sorted { $0.created < $1.created } }
    private var shown: [PunchItem] {
        all.filter { (tradeFilter.isEmpty || $0.trade == tradeFilter) && (status == "All" || (status == "Open" ? !$0.done : $0.done)) }
    }
    private var doneN: Int { all.filter { $0.done }.count }
    private var pct: Int { all.isEmpty ? 0 : Int((Double(doneN) / Double(all.count) * 100).rounded()) }
    private var trades: [String] { Array(Set(all.map { $0.trade.isEmpty ? "Other" : $0.trade })).sorted() }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Button { dismiss() } label: {
                    HStack(spacing: 6) { Image(systemName: "chevron.left").font(.title3.weight(.semibold)); Text(space == nil ? "Punch" : "Spaces").font(.title3.weight(.semibold)) }
                        .foregroundStyle(Theme.blue)
                }.buttonStyle(.plain)
                HStack(spacing: 16) {
                    RoundedRectangle(cornerRadius: 20).fill(Theme.card(dark)).frame(width: 74, height: 74)
                        .overlay(SpaceIcon(name: space?.name ?? "", symbol: space?.symbol ?? "door.left.hand.closed", size: 32))
                        .overlay(RoundedRectangle(cornerRadius: 20).stroke(Theme.border(dark), lineWidth: 1))
                    VStack(alignment: .leading, spacing: 4) {
                        Text(space?.name ?? "General").font(.system(size: 34, weight: .heavy)).minimumScaleFactor(0.6).lineLimit(1)
                        Text(((space?.level.isEmpty ?? true) ? "Other" : space!.level) + " · " + job.name).font(.title3).foregroundStyle(.secondary)
                    }
                }
                if let space {
                    HStack(spacing: 10) {
                        pill("Room", on: !space.isExterior, check: !space.isExterior) { space.isExterior = false }
                        pill("Area", on: space.isExterior, check: space.isExterior) { space.isExterior = true }
                        Spacer()
                        Menu {
                            Button("Rename") { nameText = space.name; renameOpen = true }
                            Button("Mark all done") { all.forEach { $0.done = true; $0.completed = Date() } }
                            Button("Reopen all") { all.forEach { $0.done = false; $0.completed = nil } }
                        } label: {
                            Image(systemName: "line.3.horizontal").font(.title2.weight(.bold)).foregroundStyle(.primary)
                                .frame(width: 54, height: 54)
                                .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
                                .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark), lineWidth: 1))
                        }.menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                    }
                }
                HStack {
                    Text("Progress").font(.title3).foregroundStyle(.secondary)
                    Spacer()
                    Text("\(pct)% (\(doneN)/\(all.count))").font(.title3.weight(.bold)).foregroundStyle(Theme.blue)
                }
                ProgressView(value: Double(pct) / 100).tint(Theme.blue)
                Divider()
                HStack(spacing: 12) {
                    Button { addOpen = true } label: {
                        Image(systemName: "plus").font(.title.weight(.semibold)).foregroundStyle(.white)
                            .frame(maxWidth: .infinity).frame(height: 66).background(Theme.blue, in: RoundedRectangle(cornerRadius: 18))
                    }.buttonStyle(.plain)
                    Menu {
                        ForEach(Trades.all, id: \.self) { t in
                            Button { addTrade(t) } label: { Label(t, systemImage: Trades.symbol(t)) }
                        }
                    } label: { sq("checklist") }.menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                    PhotosPicker(selection: $pick, matching: .images) { sq("camera") }.buttonStyle(.plain)
                }
                Text("CHECKLIST (\(all.count))").font(.title3.weight(.heavy)).tracking(2).foregroundStyle(.secondary).padding(.top, 10)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        chip("All \(all.count)", on: tradeFilter.isEmpty, sym: nil) { tradeFilter = "" }
                        ForEach(trades, id: \.self) { t in
                            chip("\(t) \(all.filter { ($0.trade.isEmpty ? "Other" : $0.trade) == t }.count)", on: tradeFilter == t, sym: Trades.symbol(t)) { tradeFilter = t }
                        }
                    }
                }
                Menu {
                    ForEach(["All", "Open", "Done"], id: \.self) { v in Button(v) { status = v } }
                } label: {
                    Label("Filter ▾", systemImage: "line.3.horizontal.decrease").font(.title3.weight(.bold)).foregroundStyle(.primary)
                        .frame(maxWidth: .infinity).frame(height: 54)
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
                        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark), lineWidth: 1))
                }.menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                ForEach(shown) { it in card(it) }
                if shown.isEmpty { Text("Nothing here yet.").foregroundStyle(.secondary) }
                Color.clear.frame(height: 110)
            }
            .padding(.horizontal, 16).padding(.top, 8)
        }
        .background(Theme.bg(dark))
        .navigationTitle(space?.name ?? "General")
        #if os(iOS)
        .toolbar(.hidden, for: .navigationBar)
        #endif
        .shellAdd { addOpen = true }
        .alert("Add item", isPresented: $addOpen) {
            TextField("What needs doing", text: $newText)
            Button("Add") {
                let t = newText.trimmingCharacters(in: .whitespaces)
                if !t.isEmpty {
                    let it = PunchItem(text: t, trade: tradeFilter.isEmpty ? "Other" : tradeFilter)
                    it.job = job; it.space = space; context.insert(it)
                }
                newText = ""
            }
            Button("Cancel", role: .cancel) { newText = "" }
        }
        .alert("Rename", isPresented: $renameOpen) {
            TextField("Name", text: $nameText)
            Button("Save") { let n = nameText.trimmingCharacters(in: .whitespaces); if !n.isEmpty { space?.name = n } }
            Button("Cancel", role: .cancel) {}
        }
        .confirmationDialog("Delete this item?", isPresented: Binding(get: { toDelete != nil }, set: { if !$0 { toDelete = nil } }), titleVisibility: .visible) {
            Button("Delete", role: .destructive) { if let t = toDelete { context.delete(t) }; toDelete = nil }
            Button("Cancel", role: .cancel) { toDelete = nil }
        }
        .onChange(of: pick) { _, new in
            Task {
                for it in new {
                    if let d = try? await it.loadTransferable(type: Data.self) {
                        let p = SitePhoto(data: d); p.job = job; p.space = space; context.insert(p)
                    }
                }
                pick = []
            }
        }
    }

    private func addTrade(_ t: String) {
        let it = PunchItem(text: t, trade: t); it.job = job; it.space = space; context.insert(it)
    }

    private func sq(_ sym: String) -> some View {
        Image(systemName: sym).font(.title).foregroundStyle(.primary)
            .frame(maxWidth: .infinity).frame(height: 66)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border(dark), lineWidth: 1))
    }

    private func pill(_ t: String, on: Bool, check: Bool, _ f: @escaping () -> Void) -> some View {
        Button(action: f) {
            HStack(spacing: 6) { if check { Image(systemName: "checkmark").font(.headline.weight(.bold)) }; Text(t).font(.title3.weight(.bold)) }
                .foregroundStyle(on ? Theme.purple : .secondary).padding(.horizontal, 20).frame(height: 48)
                .background(on ? Theme.purple.opacity(0.15) : Color.clear, in: Capsule())
                .overlay(Capsule().stroke(on ? Theme.purple : Theme.border(dark), lineWidth: 1.5))
        }.buttonStyle(.plain)
    }

    private func chip(_ t: String, on: Bool, sym: String?, _ f: @escaping () -> Void) -> some View {
        Button(action: f) {
            HStack(spacing: 6) { if let sym { Image(systemName: sym) }; Text(t).font(.title3.weight(.bold)) }
                .foregroundStyle(on ? Theme.blue : .primary).padding(.horizontal, 18).frame(height: 54)
                .background(on ? Theme.blue.opacity(0.14) : Color.clear, in: Capsule())
                .overlay(Capsule().stroke(on ? Theme.blue : Theme.border(dark), lineWidth: 1.5))
        }.buttonStyle(.plain)
    }

    private func card(_ it: PunchItem) -> some View {
        HStack(spacing: 14) {
            Button { it.done.toggle(); it.completed = it.done ? Date() : nil } label: {
                RoundedRectangle(cornerRadius: 12).stroke(it.done ? Theme.green : Color.secondary.opacity(0.7), lineWidth: 3)
                    .frame(width: 38, height: 38)
                    .overlay { if it.done { Image(systemName: "checkmark").font(.headline.weight(.bold)).foregroundStyle(Theme.green) } }
            }.buttonStyle(.plain)
            NavigationLink { PunchDetail(item: it) } label: {
                VStack(alignment: .leading, spacing: 2) {
                    Text(it.text.isEmpty ? "Punch item" : it.text).font(.title3.weight(.semibold)).foregroundStyle(.primary)
                        .strikethrough(it.done).multilineTextAlignment(.leading)
                    Text("Added " + it.created.formatted(.dateTime.month(.twoDigits).day(.twoDigits))).font(.headline).foregroundStyle(.secondary)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }.buttonStyle(.plain)
            NavigationLink { PunchDetail(item: it) } label: {
                let n = (it.photos ?? []).count
                ZStack(alignment: .topTrailing) {
                    RoundedRectangle(cornerRadius: 14).stroke(Color.secondary.opacity(0.5), style: StrokeStyle(lineWidth: 1.5, dash: [5, 4]))
                        .frame(width: 56, height: 56)
                        .overlay {
                            if n > 0 { PhotoStack(datas: (it.photos ?? []).sorted { $0.created > $1.created }.map { $0.data }, thumb: 36) }
                            else { Image(systemName: "camera").font(.title3).foregroundStyle(.secondary) }
                        }
                    if n > 0 { Text("\(n)").font(.caption2.weight(.bold)).foregroundStyle(.white).padding(4).background(Theme.blue, in: Circle()).offset(x: 6, y: -6) }
                }
            }.buttonStyle(.plain)
            Button { toDelete = it } label: { Image(systemName: "xmark").font(.headline).foregroundStyle(.secondary).frame(width: 30, height: 40) }.buttonStyle(.plain)
        }
        .padding(.vertical, 14).padding(.horizontal, 16)
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border(dark), lineWidth: 1))
    }
}

struct PunchDetail: View {
    @Environment(\.modelContext) private var context
    @Bindable var item: PunchItem
    @State private var pickBefore: [PhotosPickerItem] = []
    @State private var pickAfter: [PhotosPickerItem] = []
    @State private var cameraKind: String?

    private func photos(_ kind: String) -> [PunchPhoto] {
        (item.photos ?? []).filter { $0.kind == kind }.sorted { $0.created < $1.created }
    }

    @State private var valueAlert = false
    @State private var valueText = ""

    var body: some View {
        Form {
            // 1. Photos first
            gallery("Before", $pickBefore)
            gallery("After", $pickAfter)
            if !photos("Completion").isEmpty { gallery("Completion", nil) }
            // 2. Name under the photos
            Section {
                TextField("What needs doing", text: $item.text, axis: .vertical).font(.title3.weight(.semibold))
                HStack(spacing: 8) {
                    if !item.priority.isEmpty { tag(item.priority, Theme.orange) }
                    if item.value > 0 { tag("$" + item.value.formatted(.number.precision(.fractionLength(0...2))), Theme.blue) }
                    if item.done { tag("Done", Theme.green) }
                }
            }
            Section("Notes") { TextEditor(text: $item.extraNotes).frame(minHeight: 70) }
        }
        .formStyle(.grouped)
        .navigationTitle(item.text.isEmpty ? "Punch item" : item.text)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Menu {
                    Picker("Priority", selection: $item.priority) {
                        Text("None").tag("")
                        ForEach(["Normal", "High", "Critical"], id: \.self) { Text($0).tag($0) }
                    }
                    Button { valueText = item.value == 0 ? "" : String(item.value); valueAlert = true } label: { Label("Value…", systemImage: "dollarsign.circle") }
                    Toggle("Done", isOn: $item.done)
                } label: { Image(systemName: "line.3.horizontal") }
            }
        }
        .onChange(of: item.done) { _, now in item.completed = now ? Date() : nil }
        .alert("Value", isPresented: $valueAlert) {
            #if os(iOS)
            TextField("0", text: $valueText).keyboardType(.decimalPad)
            #else
            TextField("0", text: $valueText)
            #endif
            Button("Save") { item.value = Double(valueText.replacingOccurrences(of: ",", with: "")) ?? 0 }
            Button("Cancel", role: .cancel) {}
        }
        #if os(iOS)
        .fullScreenCover(isPresented: Binding(get: { cameraKind != nil }, set: { if !$0 { cameraKind = nil } })) {
            CameraPicker { d in
                let pp = PunchPhoto(data: d, kind: cameraKind ?? "Before")
                context.insert(pp); pp.item = item
            }.ignoresSafeArea()
        }
        #endif
    }

    @ViewBuilder private func gallery(_ kind: String, _ picks: Binding<[PhotosPickerItem]>?) -> some View {
        Section("\(kind) photos · \(photos(kind).count)") {
            ForEach(photos(kind)) { p in
                if let d = p.data, let img = PhotoThumb.small(d, 1000) {
                    NavigationLink { MarkupView(data: d) { p.data = $0 } } label: {
                        img.resizable().scaledToFit().frame(maxHeight: 340)
                    }.buttonStyle(.plain)
                }
            }
            .onDelete { idx in let l = photos(kind); idx.forEach { context.delete(l[$0]) } }
            if picks != nil {
                #if os(iOS)
                if CameraPicker.available { Button { cameraKind = kind } label: { Label("Take \(kind.lowercased()) photo", systemImage: "camera") } }
                #endif
            }
            if let picks {
                PhotosPicker(selection: picks, matching: .images) { Label("Add \(kind.lowercased()) photo", systemImage: "photo.badge.plus") }
                    .onChange(of: picks.wrappedValue) { _, new in
                        Task {
                            for it in new {
                                if let d = try? await it.loadTransferable(type: Data.self) {
                                    let pp = PunchPhoto(data: d, kind: kind)
                                    context.insert(pp); pp.item = item
                                }
                            }
                            picks.wrappedValue = []
                        }
                    }
            }
        }
    }

    private func tag(_ t: String, _ c: Color) -> some View {
        Text(t).font(.subheadline.weight(.bold)).foregroundStyle(c)
            .padding(.horizontal, 10).padding(.vertical, 4).background(c.opacity(0.15), in: Capsule())
    }
}


/// Every open checklist item on the job, grouped by space — opened from the Progress bar.
struct OpenItemsView: View {
    let job: Job
    @AppStorage("bpDark") private var dark = true
    private var open: [PunchItem] { (job.punchItems ?? []).filter { !$0.done } }
    private var groups: [(String, [PunchItem])] {
        let d = Dictionary(grouping: open) { $0.space?.name ?? "General" }
        return d.keys.sorted().map { ($0, (d[$0] ?? []).sorted { $0.created < $1.created }) }
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                Text("\(open.count) open item\(open.count == 1 ? "" : "s")").font(.title2.weight(.heavy))
                if open.isEmpty {
                    Text("Nothing open. Every checklist item is done.").foregroundStyle(.secondary).padding(.top, 20)
                }
                ForEach(groups, id: \.0) { name, items in
                    Text(name.uppercased()).font(.subheadline.weight(.heavy)).foregroundStyle(.secondary).padding(.top, 8)
                    ForEach(items) { it in
                        HStack(spacing: 14) {
                            Button { it.done = true; it.completed = Date() } label: {
                                RoundedRectangle(cornerRadius: 10).stroke(Color.secondary.opacity(0.7), lineWidth: 3).frame(width: 34, height: 34)
                            }.buttonStyle(.plain)
                            NavigationLink { PunchDetail(item: it) } label: {
                                Text(it.text.isEmpty ? "Punch item" : it.text).font(.title3.weight(.semibold)).foregroundStyle(.primary)
                                    .multilineTextAlignment(.leading).frame(maxWidth: .infinity, alignment: .leading)
                            }.buttonStyle(.plain)
                        }
                        .padding(14)
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
                        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark), lineWidth: 1))
                    }
                }
            }.padding(16).padding(.bottom, 90)
        }
        .navigationTitle("Open items")
    }
}
