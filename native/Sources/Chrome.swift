import SwiftUI
import SwiftData

// MARK: - Shared screen chrome (same bones as the web field app)

/// What the floating "+" does on the screen you're looking at.
@MainActor
final class ShellState: ObservableObject {
    @Published var addSymbol = "plus"
    @Published var addAction: (() -> Void)?
    var owner: UUID?
    @Published var barHidden = false
    var goHome: () -> Void = {}
}

private struct ShellAdd: ViewModifier {
    @EnvironmentObject var shell: ShellState
    let symbol: String
    let action: () -> Void
    @State private var token = UUID()
    func body(content: Content) -> some View {
        content
            .onAppear { shell.owner = token; shell.addSymbol = symbol; shell.addAction = action }
            .onDisappear { if shell.owner == token { shell.owner = nil; shell.addAction = nil } }
    }
}

extension View {
    /// Wires the floating + button to this screen.
    func shellAdd(symbol: String = "plus", _ action: @escaping () -> Void) -> some View { modifier(ShellAdd(symbol: symbol, action: action)) }
}

/// The floating row in the bottom-right corner: back · + · ••• · 🎤
struct FloatBar: View {
    @EnvironmentObject var shell: ShellState
    @Environment(\.openMenu) private var openMenu
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpActiveJob") private var activeKey = ""
    @StateObject private var voice = Dictation()
    @State private var saved = ""
    let showBack: Bool
    @AppStorage("bpDark") private var dark = true

    private var activeJob: Job? { jobs.first { String($0.created.timeIntervalSince1970) == activeKey } ?? jobs.first { $0.isActive } ?? jobs.first }

    var body: some View {
        VStack(alignment: .trailing, spacing: 10) {
            if voice.listening || !voice.message.isEmpty || !saved.isEmpty { banner }
            HStack(spacing: 14) {
                if showBack { circle("chevron.left", filled: nil) { shell.goHome() } }
                if let add = shell.addAction { circle(shell.addSymbol, filled: Theme.blue) { add() } }
                circle("ellipsis", filled: nil) { openMenu() }
                circle(voice.listening ? "stop.fill" : "mic.fill", filled: Theme.red) { toggleVoice() }
            }
        }
        .padding(.trailing, 18).padding(.bottom, 14)
        .offset(y: shell.barHidden && !voice.listening ? 140 : 0)
        .opacity(shell.barHidden && !voice.listening ? 0 : 1)
        .animation(.easeOut(duration: 0.2), value: shell.barHidden)
    }

    private var banner: some View {
        Text(voice.listening ? (voice.text.isEmpty ? "Listening… tap ■ to save a note" : voice.text)
                             : (voice.message.isEmpty ? saved : voice.message))
            .font(.callout.weight(.semibold)).multilineTextAlignment(.leading)
            .padding(12).frame(maxWidth: 300, alignment: .leading)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark)))
            .lineLimit(5)
    }

    private func toggleVoice() {
        saved = ""
        if voice.listening {
            let heard = voice.stop()
            guard !heard.isEmpty else { return }
            guard let job = activeJob else { saved = "Heard: \(heard) — add a job first to save it."; return }
            let n = JobNote(title: "Voice note")
            n.text = heard
            context.insert(n)
            n.job = job
            saved = "Saved to \(job.name) → Project Notes"
        } else {
            voice.start()
        }
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
            .sheet(isPresented: $adding) { NewJobSheet() }
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


// MARK: - New Job sheet (matches the web "New Job" form)

struct NewJobSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @AppStorage("bpDark") private var dark = true
    @State private var name = ""
    @State private var street = ""
    @State private var city = ""
    @State private var state = "NJ"
    @State private var zip = ""
    @State private var client = ""
    @State private var email = ""
    @State private var cell = ""
    @State private var contract = ""
    @State private var status = "Active"
    @State private var hasStart = false
    @State private var start = Date()
    @State private var hasEnd = false
    @State private var end = Date()
    @State private var notes = ""
    @State private var level = "Level 1"
    @State private var picked: [(String, String)] = []     // (room, level)
    @State private var custom = ""
    @StateObject private var voice = Dictation()

    private let quick = ["Kitchen", "Bathroom", "Basement Bath", "Master Bath", "Half Bath", "Bedroom 1", "Bedroom 2", "Bedroom 3",
                         "Living Room", "Dining Room", "Basement", "Attic", "Garage", "Office", "Foyer", "Hallway", "Stairs",
                         "Laundry", "Utility Room", "Boiler Room", "Closet"]

    private func field(_ title: String, _ text: Binding<String>, _ prompt: String, keyboard: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased()).font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
            TextField(prompt, text: text).textFieldStyle(.plain).font(.title3)
                .padding(.horizontal, 16).frame(height: 54)
                .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("New Job").font(.title.weight(.heavy))
                Spacer()
                Button { dismiss() } label: {
                    Image(systemName: "xmark").font(.headline).foregroundStyle(.primary).frame(width: 40, height: 40)
                        .background(Theme.border(dark).opacity(0.6), in: Circle())
                }.buttonStyle(.plain)
            }.padding(.horizontal, 20).padding(.vertical, 14)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    ZStack(alignment: .topTrailing) {
                        field("Job name *", $name, "e.g. Smith Kitchen Reno")
                        Button { toggleVoice() } label: {
                            Label(voice.listening ? "Stop" : "Speak", systemImage: "mic.fill").font(.title3.weight(.bold)).foregroundStyle(.white)
                                .padding(.horizontal, 18).frame(height: 44).background(voice.listening ? Theme.red : Theme.blue, in: Capsule())
                        }.buttonStyle(.plain).offset(y: -4)
                    }
                    field("Job address", $street, "Street address")
                    HStack(alignment: .top, spacing: 12) {
                        field("City", $city, "City")
                        field("State", $state, "NJ").frame(width: 80)
                        field("Zip code", $zip, "Zip").frame(width: 110)
                    }
                    field("Client name", $client, "Client name")
                    field("Client email", $email, "client@example.com")
                    field("Client cell", $cell, "(123)-456-7890")
                    field("Contract value ($)", $contract, "0.00")
                    VStack(alignment: .leading, spacing: 8) {
                        Text("STATUS").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                        Picker("", selection: $status) { ForEach(["Active", "On hold", "Complete"], id: \.self) { Text($0) } }
                            .pickerStyle(.segmented).labelsHidden()
                    }
                    Toggle("Start date", isOn: $hasStart).font(.title3)
                    if hasStart { DatePicker("", selection: $start, displayedComponents: .date).labelsHidden() }
                    Toggle("Completion date", isOn: $hasEnd).font(.title3)
                    if hasEnd { DatePicker("", selection: $end, displayedComponents: .date).labelsHidden() }
                    Text("ROOMS").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary).padding(.top, 6)
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack { ForEach(["Basement", "Level 1", "Level 2", "Level 3", "Roof", "Outside"], id: \.self) { l in
                            Button(l) { level = l }.font(.headline.weight(.bold))
                                .foregroundStyle(level == l ? Theme.blue : .primary).padding(.horizontal, 14).frame(height: 40)
                                .background(level == l ? Theme.blue.opacity(0.15) : Color.clear, in: Capsule())
                                .overlay(Capsule().stroke(level == l ? Theme.blue : Theme.border(dark), lineWidth: 1.5)).buttonStyle(.plain)
                        } }
                    }
                    FlowChips(items: quick) { r in add(r) }
                    HStack(spacing: 12) {
                        TextField("Type your own on \(level)…", text: $custom).textFieldStyle(.plain).font(.title3)
                            .padding(.horizontal, 14).frame(height: 54)
                            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))
                            .onSubmit { add(custom); custom = "" }
                        Button("Add") { add(custom); custom = "" }.font(.title3.weight(.bold)).foregroundStyle(.white)
                            .padding(.horizontal, 22).frame(height: 54).background(Theme.blue, in: RoundedRectangle(cornerRadius: 14)).buttonStyle(.plain)
                    }
                    if picked.isEmpty { Text("Nothing picked yet. You can always add rooms later.").foregroundStyle(.secondary) }
                    else {
                        ForEach(Array(picked.enumerated()), id: \.offset) { i, p in
                            HStack { Text("\(p.1) · \(p.0)").font(.headline); Spacer()
                                Button { picked.remove(at: i) } label: { Image(systemName: "xmark").foregroundStyle(.secondary) }.buttonStyle(.plain) }
                        }
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        Text("NOTES").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                        TextEditor(text: $notes).font(.title3).scrollContentBackground(.hidden).padding(8).frame(height: 110)
                            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))
                    }
                    Button { create() } label: {
                        Text("Create Job").font(.title3.weight(.bold)).foregroundStyle(.white).frame(maxWidth: .infinity).frame(height: 58)
                            .background(name.trimmingCharacters(in: .whitespaces).isEmpty ? Theme.blue.opacity(0.4) : Theme.blue, in: RoundedRectangle(cornerRadius: 16))
                    }.buttonStyle(.plain).disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
                .padding(20)
            }
        }
        .background(Theme.bg(dark))
        #if os(macOS)
        .frame(minWidth: 460, minHeight: 640)
        #endif
        .onChange(of: voice.text) { _, t in if voice.listening { name = t } }
    }

    private func toggleVoice() {
        if voice.listening { let h = voice.stop(); if !h.isEmpty { name = h } } else { voice.start() }
    }

    private func add(_ room: String) {
        let r = room.trimmingCharacters(in: .whitespaces)
        guard !r.isEmpty, !picked.contains(where: { $0.0 == r && $0.1 == level }) else { return }
        picked.append((r, level))
    }

    private func create() {
        let n = name.trimmingCharacters(in: .whitespaces)
        guard !n.isEmpty else { return }
        let j = Job(name: n)
        let cityLine = [city, [state, zip].filter { !$0.isEmpty }.joined(separator: " ")].filter { !$0.isEmpty }.joined(separator: ", ")
        j.address = [street, cityLine].filter { !$0.isEmpty }.joined(separator: ", ")
        j.client = client; j.clientEmail = email; j.clientPhone = cell
        j.contract = Double(contract.replacingOccurrences(of: ",", with: "")) ?? 0
        j.status = status; j.isActive = status != "Complete"
        j.startDate = hasStart ? start : nil; j.completionDate = hasEnd ? end : nil
        j.jobNotes = notes
        context.insert(j)
        for (i, p) in picked.enumerated() {
            let sp = Space(name: p.0, level: p.1, order: i, isExterior: p.1 == "Outside")
            sp.job = j; context.insert(sp)
        }
        dismiss()
    }
}

/// Wrapping row of "+ Name" pills.
struct FlowChips: View {
    let items: [String]
    let tap: (String) -> Void
    @AppStorage("bpDark") private var dark = true
    var body: some View {
        FlowLayout(spacing: 10) {
            ForEach(items, id: \.self) { t in
                Button { tap(t) } label: {
                    Text("+ " + t).font(.title3.weight(.bold)).foregroundStyle(.primary)
                        .padding(.horizontal, 18).frame(height: 48)
                        .overlay(Capsule().stroke(Theme.border(dark), lineWidth: 1.5))
                }.buttonStyle(.plain)
            }
        }
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let w = proposal.width ?? 400
        var x: CGFloat = 0, y: CGFloat = 0, row: CGFloat = 0
        for v in subviews {
            let s = v.sizeThatFits(.unspecified)
            if x + s.width > w { x = 0; y += row + spacing; row = 0 }
            x += s.width + spacing; row = max(row, s.height)
        }
        return CGSize(width: w, height: y + row)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, row: CGFloat = 0
        for v in subviews {
            let s = v.sizeThatFits(.unspecified)
            if x + s.width > bounds.maxX { x = bounds.minX; y += row + spacing; row = 0 }
            v.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(s))
            x += s.width + spacing; row = max(row, s.height)
        }
    }
}
