import SwiftUI
import SwiftData

struct PunchListView: View {
    @Environment(\.modelContext) private var context
    let job: Job
    let space: Space?              // nil = General
    @State private var showDone = false
    @State private var trade = ""
    @State private var text = ""

    private var items: [PunchItem] {
        (job.punchItems ?? [])
            .filter { $0.space?.uid == space?.uid && (showDone || !$0.done) }
            .sorted { $0.created > $1.created }
    }

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
            Section(showDone ? "All items" : "Open items") {
                ForEach(items) { item in
                    Button {
                        item.done.toggle(); item.completed = item.done ? Date() : nil
                    } label: {
                        HStack {
                            Image(systemName: item.done ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(item.done ? .green : .secondary)
                            Text(item.text).strikethrough(item.done).foregroundStyle(.primary)
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(items[$0]) } }
            }
        }
        .navigationTitle(space?.name ?? "General")
        .toolbar {
            Menu {
                Toggle("Show done items", isOn: $showDone)
            } label: { Image(systemName: "line.3.horizontal.decrease.circle") }
        }
    }

    private func add() {
        let note = text.trimmingCharacters(in: .whitespaces)
        let item = PunchItem(text: note.isEmpty ? trade : "\(trade) – \(note)", trade: trade)
        item.job = job; item.space = space
        context.insert(item)
        text = ""
    }
}
