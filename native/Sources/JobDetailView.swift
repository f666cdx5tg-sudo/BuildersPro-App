import SwiftUI
import SwiftData

enum Section3: String, CaseIterable, Identifiable {
    case spaces = "Spaces", punch = "Punch", photos = "Photos"
    var id: String { rawValue }
    var symbol: String { self == .spaces ? "square.grid.2x2" : self == .punch ? "checklist" : "photo.on.rectangle" }
}

struct JobDetailView: View {
    @Bindable var job: Job
    @State private var section: Section3 = .spaces
    @State private var addingSpace = false
    @State private var newSpace = ""

    var body: some View {
        VStack(spacing: 0) {
            // progress line: "91% (20/22) · 2 left"
            HStack {
                Text("Progress").font(.caption).foregroundStyle(.secondary)
                Spacer()
                Text("\(job.percent)% (\(job.doneCount)/\(job.totalCount))" +
                     (job.totalCount > job.doneCount ? " · \(job.totalCount - job.doneCount) left" : " ✓"))
                    .font(.caption.bold())
            }.padding(.horizontal).padding(.top, 8)

            Picker("Section", selection: $section) {
                ForEach(Section3.allCases) { Label($0.rawValue, systemImage: $0.symbol).tag($0) }
            }.pickerStyle(.segmented).padding()

            SpaceGrid(job: job, mode: section)
        }
        .navigationTitle(job.name)
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .toolbar {
            // one button holds the options (standing rule)
            Menu { Button("Add a space", systemImage: "plus.square") { addingSpace = true } }
                label: { Image(systemName: "line.3.horizontal") }
        }
        .alert("New space", isPresented: $addingSpace) {
            TextField("Name (Kitchen, Roof…)", text: $newSpace)
            Button("Add") { addSpace() }
            Button("Cancel", role: .cancel) { newSpace = "" }
        }
    }

    private func addSpace() {
        let n = newSpace.trimmingCharacters(in: .whitespaces); newSpace = ""
        guard !n.isEmpty else { return }
        let s = Space(name: n, level: "Level 1", order: (job.spaces ?? []).count)
        s.job = job
        job.spaces?.append(s)
    }
}
