import SwiftUI
import SwiftData

// MARK: - Shared screen chrome (same bones as the web field app)

/// What the floating "+" does on the screen you're looking at.
@MainActor
final class ShellState: ObservableObject {
    @Published var addSymbol = "plus"
    @Published var addAction: (() -> Void)?
    var goHome: () -> Void = {}
}

private struct ShellAdd: ViewModifier {
    @EnvironmentObject var shell: ShellState
    let symbol: String
    let action: () -> Void
    func body(content: Content) -> some View {
        content
            .onAppear { shell.addSymbol = symbol; shell.addAction = action }
            .onDisappear { shell.addAction = nil }
    }
}

extension View {
    /// Wires the floating + button to this screen.
    func shellAdd(symbol: String = "plus", _ action: @escaping () -> Void) -> some View { modifier(ShellAdd(symbol: symbol, action: action)) }
}

/// The floating row in the bottom-right corner: back · + · ☰
struct FloatBar: View {
    @EnvironmentObject var shell: ShellState
    @Environment(\.openMenu) private var openMenu
    let showBack: Bool
    @AppStorage("bpDark") private var dark = true

    var body: some View {
        HStack(spacing: 14) {
            if showBack { circle("chevron.left", filled: nil) { shell.goHome() } }
            if let add = shell.addAction { circle(shell.addSymbol, filled: Theme.blue) { add() } }
            circle("line.3.horizontal", filled: nil) { openMenu() }
        }
        .padding(.trailing, 18).padding(.bottom, 14)
    }

    private func circle(_ symbol: String, filled: Color?, _ tap: @escaping () -> Void) -> some View {
        Button(action: tap) {
            Image(systemName: symbol).font(.system(size: 20, weight: .bold))
                .foregroundStyle(filled == nil ? Color.primary : Color.white)
                .frame(width: 50, height: 50)
                .background(filled ?? Theme.card(dark).opacity(0.92), in: Circle())
                .overlay(Circle().stroke(filled == nil ? Color.primary.opacity(0.35) : Color.clear, lineWidth: 1.5))
                .shadow(color: (filled ?? .black).opacity(0.35), radius: 8, y: 3)
        }.buttonStyle(.plain)
    }
}

/// Big title, blue date·time, gray subtitle.
struct TopBar: View {
    let title: String
    let sub: String
    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title).font(.system(size: 40, weight: .heavy)).minimumScaleFactor(0.6).lineLimit(1)
            TimelineView(.everyMinute) { ctx in
                Text(ctx.date.formatted(.dateTime.month(.twoDigits).day(.twoDigits).year()) + " · " + ctx.date.formatted(.dateTime.hour().minute()))
                    .font(.headline.weight(.semibold)).foregroundStyle(Theme.blue)
            }
            if !sub.isEmpty { Text(sub).font(.title3).foregroundStyle(.secondary) }
        }
    }
}

extension Theme {
    static let red = Color(red: 1.0, green: 0.27, blue: 0.23)
    static let green = Color(red: 0.19, green: 0.82, blue: 0.35)
    static let yellow = Color(red: 1.0, green: 0.84, blue: 0.04)
    static let purple = Color(red: 0.75, green: 0.35, blue: 0.95)
    static let brown = Color(red: 0.64, green: 0.52, blue: 0.37)
    static let teal = Color(red: 0.0, green: 0.78, blue: 0.75)
    static let lightBlue = Color(red: 0.26, green: 0.64, blue: 0.96)
}

/// A rounded dark card.
struct CardBox<Content: View>: View {
    @AppStorage("bpDark") private var dark = true
    var stroke: Color? = nil
    @ViewBuilder var content: Content
    var body: some View {
        content
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 20))
            .overlay(RoundedRectangle(cornerRadius: 20).stroke(stroke ?? Theme.border(dark), lineWidth: 1))
    }
}

// MARK: - Jobs

struct JobsView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @State private var newName = ""
    @State private var adding = false
    @State private var asking = false
    @State private var picking = false
    @State private var importing = false
    @State private var report = ""
    @State private var showReport = false
    @State private var tab = 0

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    TopBar(title: "Jobs", sub: "\(jobs.filter { $0.isActive }.count) active · \(jobs.count) total")
                    tabs
                    if tab == 0 {
                        ForEach(jobs) { job in
                            NavigationLink(value: job) { JobCardFull(job: job) }.buttonStyle(.plain)
                                .contextMenu { Button("Delete job", systemImage: "trash", role: .destructive) { context.delete(job) } }
                        }
                        if jobs.isEmpty && !importing {
                            ContentUnavailableView("No jobs yet", systemImage: "hammer", description: Text("Tap + to add a job or import your backup."))
                        }
                    } else {
                        ContentUnavailableView("No estimates yet", systemImage: "doc.text", description: Text("Estimates are coming to the native app."))
                    }
                    Spacer(minLength: 90)
                }
                .padding(.horizontal, 16).padding(.top, 8)
            }
            .background(Theme.bg(dark))
            .navigationDestination(for: Job.self) { JobDetailView(job: $0) }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
            .shellAdd { asking = true }
            .confirmationDialog("Jobs", isPresented: $asking) {
                Button("Add a job") { adding = true }
                Button("Import backup file…") { picking = true }
            }
            .alert("New job", isPresented: $adding) {
                TextField("Job name", text: $newName)
                Button("Add") {
                    let n = newName.trimmingCharacters(in: .whitespaces)
                    if !n.isEmpty { context.insert(Job(name: n)) }
                    newName = ""
                }
                Button("Cancel", role: .cancel) { newName = "" }
            }
            .fileImporter(isPresented: $picking, allowedContentTypes: [.json]) { result in
                switch result {
                case .success(let url): runImport(url)
                case .failure(let error): report = error.localizedDescription; showReport = true
                }
            }
            .alert("Import", isPresented: $showReport) { Button("OK", role: .cancel) {} } message: { Text(report) }
            .overlay { if importing { ProgressView("Importing your jobs…").padding(24).background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14)) } }
        }
    }

    private var tabs: some View {
        HStack(spacing: 10) {
            tabButton("Jobs", 0)
            tabButton("Estimates", 1)
        }
    }

    private func tabButton(_ title: String, _ i: Int) -> some View {
        Button { tab = i } label: {
            Text(title).font(.headline.weight(.heavy)).frame(maxWidth: .infinity, minHeight: 46)
                .foregroundStyle(tab == i ? Theme.orange : .secondary)
                .background(tab == i ? Theme.orange.opacity(0.14) : Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(tab == i ? Theme.orange : Theme.border(dark), lineWidth: 1.5))
        }.buttonStyle(.plain)
    }

    private func runImport(_ url: URL) {
        importing = true
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 300_000_000)
            do { report = try BackupImporter.run(url: url, context: context).text }
            catch { report = "Could not import: \(error.localizedDescription)" }
            importing = false
            showReport = true
        }
    }
}

/// The job card as it looks in the web app's Jobs list.
struct JobCardFull: View {
    let job: Job
    @AppStorage("bpDark") private var dark = true

    private func usd(_ v: Double) -> String { v.formatted(.currency(code: "USD").precision(.fractionLength(0))) }
    private var areasDone: Int { (job.spaces ?? []).filter { $0.openCount == 0 && $0.doneCount > 0 }.count }
    private var statusText: String { job.status.isEmpty ? (job.isActive ? "Active" : "Complete") : job.status }

    var body: some View {
        CardBox {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .center, spacing: 12) {
                    Circle().fill(Theme.lightBlue).frame(width: 12, height: 12)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(job.name).font(.system(size: 26, weight: .heavy)).lineLimit(2).minimumScaleFactor(0.7)
                        Group {
                            if !job.address.isEmpty { Text(job.address) }
                            if !job.client.isEmpty { Text(job.client) }
                            if !job.clientEmail.isEmpty { Text(job.clientEmail) }
                            if !job.clientPhone.isEmpty { Text(job.clientPhone) }
                        }.font(.title3).foregroundStyle(.secondary)
                        if job.contract > 0 { Text(usd(job.contract)).font(.title3.weight(.heavy)) }
                    }
                    Spacer(minLength: 6)
                    Text(statusText).font(.subheadline.weight(.bold)).foregroundStyle(Theme.lightBlue)
                        .padding(.horizontal, 12).padding(.vertical, 6)
                        .background(Theme.lightBlue.opacity(0.12), in: Capsule())
                        .overlay(Capsule().stroke(Theme.lightBlue.opacity(0.5)))
                }
                HStack(spacing: 12) {
                    Text("Progress").foregroundStyle(.secondary)
                    ProgressView(value: Double(job.percent), total: 100).tint(Theme.blue)
                    Text("\(job.percent)%").font(.headline.weight(.heavy))
                }.font(.title3)
                Divider()
                row("Received to date", usd(job.collected), Theme.green)
                row("Balance owed", usd(max(0, job.revisedContract - job.collected)), Theme.red)
                if let d = job.startDate { dateRow("Started", d, Theme.green) }
                if let d = job.completionDate { dateRow("Done", d, .primary) }
                HStack(spacing: 10) {
                    chip("\((job.photos ?? []).count) photos", Theme.lightBlue, nil)
                    chip("\(areasDone)/\((job.spaces ?? []).count) areas done", Theme.red, "door.left.hand.closed")
                }
            }
        }
    }

    private func row(_ a: String, _ b: String, _ c: Color) -> some View {
        HStack { Text(a).foregroundStyle(.secondary); Spacer(); Text(b).font(.title3.weight(.heavy)).foregroundStyle(c) }.font(.title3)
    }

    private func dateRow(_ a: String, _ d: Date, _ c: Color) -> some View {
        HStack(spacing: 10) {
            Image(systemName: "checkmark.square.fill").font(.title2).foregroundStyle(Theme.blue)
            Text(a).font(.title3.weight(a == "Started" ? .heavy : .regular)).foregroundStyle(a == "Started" ? c : .secondary)
            Spacer()
            Text(d.formatted(.dateTime.month(.twoDigits).day(.twoDigits).year())).font(.title3.weight(.heavy)).foregroundStyle(c)
        }
    }

    private func chip(_ text: String, _ color: Color, _ symbol: String?) -> some View {
        HStack(spacing: 6) {
            if let symbol { Image(systemName: symbol) }
            Text(text)
        }
        .font(.callout.weight(.bold)).foregroundStyle(color)
        .padding(.horizontal, 12).padding(.vertical, 7)
        .background(color.opacity(0.10), in: Capsule())
        .overlay(Capsule().stroke(color.opacity(0.55)))
    }
}
