import SwiftUI
import SwiftData
import PhotosUI

struct PunchListView: View {
    @Environment(\.modelContext) private var context
    let job: Job
    let space: Space?              // nil = General
    @State private var trade = ""
    @State private var text = ""

    private var all: [PunchItem] {
        (job.punchItems ?? []).filter { $0.space?.uid == space?.uid }.sorted { $0.created > $1.created }
    }
    private var open: [PunchItem] { all.filter { !$0.done } }
    private var done: [PunchItem] { all.filter { $0.done } }

    var body: some View {
        List {
            Section {
                // Category is a single button that holds the options
                Menu {
                    ForEach(Trades.all, id: \.self) { t in
                        Button { trade = t } label: { Label(t, systemImage: Trades.symbol(t)) }
                    }
                } label: {
                    HStack {
                        Text(trade.isEmpty ? "Choose a category" : trade).fontWeight(.bold)
                        Spacer(); Image(systemName: "line.3.horizontal")
                    }
                }
                TextField("Note (optional)", text: $text)
                Button("Add punch item") { add() }.disabled(trade.isEmpty)
            }
            Section("Open · \(open.count)") {
                if open.isEmpty { Text("Nothing open here.").foregroundStyle(.secondary) }
                rows(open)
            }
            Section("Done · \(done.count)") {
                if done.isEmpty { Text("Nothing done yet.").foregroundStyle(.secondary) }
                rows(done)
            }
        }
        .navigationTitle(space?.name ?? "General")
    }

    @ViewBuilder private func rows(_ items: [PunchItem]) -> some View {
        ForEach(items) { item in
            HStack {
                Button {
                    item.done.toggle(); item.completed = item.done ? Date() : nil
                } label: {
                    Image(systemName: item.done ? "checkmark.circle.fill" : "circle").font(.title3)
                        .foregroundStyle(item.done ? Color.green : Color.secondary)
                }.buttonStyle(.plain)
                NavigationLink { PunchDetail(item: item) } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.text.isEmpty ? "Punch item" : item.text).strikethrough(item.done)
                        let n = (item.photos ?? []).count
                        let bits = [item.priority, n > 0 ? "\(n) photo\(n == 1 ? "" : "s")" : ""].filter { !$0.isEmpty }
                        if !bits.isEmpty { Text(bits.joined(separator: " · ")).font(.callout).foregroundStyle(.secondary) }
                    }
                }
            }
        }
        .onDelete { idx in idx.forEach { context.delete(items[$0]) } }
    }

    private func add() {
        let note = text.trimmingCharacters(in: .whitespaces)
        let item = PunchItem(text: note.isEmpty ? trade : "\(trade) – \(note)", trade: trade)
        item.job = job; item.space = space
        context.insert(item)
        text = ""
    }
}

struct PunchDetail: View {
    @Environment(\.modelContext) private var context
    @Bindable var item: PunchItem
    @State private var pickBefore: [PhotosPickerItem] = []
    @State private var pickAfter: [PhotosPickerItem] = []

    private func photos(_ kind: String) -> [PunchPhoto] {
        (item.photos ?? []).filter { $0.kind == kind }.sorted { $0.created < $1.created }
    }

    var body: some View {
        Form {
            Section("Item") {
                TextField("What needs doing", text: $item.text, axis: .vertical)
                Picker("Priority", selection: $item.priority) {
                    Text("None").tag("")
                    ForEach(["Normal", "High", "Critical"], id: \.self) { Text($0).tag($0) }
                }
                HStack { Text("Value"); Spacer(); TextField("0", value: $item.value, format: .number).multilineTextAlignment(.trailing).frame(width: 110) }
                Toggle("Done", isOn: $item.done)
                    .onChange(of: item.done) { _, now in item.completed = now ? Date() : nil }
            }
            Section("Notes") { TextEditor(text: $item.extraNotes).frame(minHeight: 70) }
            gallery("Before", $pickBefore)
            gallery("After", $pickAfter)
            if !photos("Completion").isEmpty { gallery("Completion", nil) }
        }
        .formStyle(.grouped)
        .navigationTitle(item.text.isEmpty ? "Punch item" : item.text)
    }

    @ViewBuilder private func gallery(_ kind: String, _ picks: Binding<[PhotosPickerItem]>?) -> some View {
        Section("\(kind) photos · \(photos(kind).count)") {
            ForEach(photos(kind)) { p in
                if let d = p.data, let img = PhotoThumb.image(d) { img.resizable().scaledToFit().frame(maxHeight: 340) }
            }
            .onDelete { idx in let l = photos(kind); idx.forEach { context.delete(l[$0]) } }
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
}
