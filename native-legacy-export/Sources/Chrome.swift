import SwiftUI
import PhotosUI
import SwiftData

// MARK: - Shared screen chrome (same bones as the web field app)

/// What the floating "+" does on the screen you're looking at.
@MainActor
final class ShellState: ObservableObject {
    struct Entry { let token: UUID; let symbol: String; let action: () -> Void }
    private var stack: [Entry] = []
    @Published var addSymbol = "plus"
    @Published var addAction: (() -> Void)?
    @Published var barHidden = false
    @Published var sizePop = false
    var goHome: () -> Void = {}

    func register(_ e: Entry) {
        stack.removeAll { $0.token == e.token }
        stack.append(e); refresh()
    }
    func unregister(_ t: UUID) { stack.removeAll { $0.token == t }; refresh() }
    private func refresh() {
        addSymbol = stack.last?.symbol ?? "plus"
        addAction = stack.last?.action
    }
}

private struct ShellAdd: ViewModifier {
    @EnvironmentObject var shell: ShellState
    let symbol: String
    let action: () -> Void
    @State private var token = UUID()
    func body(content: Content) -> some View {
        content
            .onAppear { shell.register(.init(token: token, symbol: symbol, action: action)) }
            .onDisappear { shell.unregister(token) }
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
    var showMenu = true            // the ••• opens the slide-out menu; Command Center's sidebar is always open, so it hides it
    @AppStorage("bpDark") private var dark = true

    private var activeJob: Job? { jobs.first { String($0.created.timeIntervalSince1970) == activeKey } ?? jobs.first { $0.isActive } ?? jobs.first }

    var body: some View {
        VStack(alignment: .trailing, spacing: 10) {
            if voice.listening || !voice.message.isEmpty || !saved.isEmpty { banner }
            HStack(spacing: 14) {
                if showBack { circle("chevron.left", filled: nil) { shell.goHome() } }
                if let add = shell.addAction { circle(shell.addSymbol, filled: Theme.blue) { add() } }
                if showMenu { circle("ellipsis", filled: nil) { openMenu() } }
                circle(voice.listening ? "stop.fill" : "mic.fill", filled: Theme.red) { toggleVoice() }
            }
        }
        .padding(.trailing, 18).padding(.bottom, 14)
        .offset(y: shell.barHidden && !voice.listening ? 140 : 0)
        .opacity(shell.barHidden && !voice.listening ? 0 : 1)
        .animation(.easeOut(duration: 0.2), value: shell.barHidden)
        // the "Saved to…" / error banner clears itself
        .task(id: saved + "|" + voice.message) {
            guard !saved.isEmpty || !voice.message.isEmpty else { return }
            try? await Task.sleep(nanoseconds: 3_500_000_000)
            if !voice.listening { saved = ""; voice.message = "" }
        }
    }

    private var banner: some View {
        Text(voice.listening ? (voice.text.isEmpty ? "Listening… tap ■ to save a note" : voice.text)
                             : (voice.message.isEmpty ? saved : voice.message))
            .font(.callout.weight(.semibold)).multilineTextAlignment(.leading)
            .padding(12).frame(maxWidth: 300, alignment: .leading)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark)))
            .lineLimit(5)
            .onTapGesture { if !voice.listening { saved = ""; voice.message = "" } }
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
    @Query(sort: \Estimate.created, order: .reverse) private var estimates: [Estimate]
    @State private var estSheet: EstimateRequest?
    @State private var openJob: Job?
    @State private var editingJob: Job?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    TopBar(title: "Jobs", sub: tab == 1 ? "\(estimates.count) estimate\(estimates.count == 1 ? "" : "s")" : "\(jobs.filter { $0.isActive }.count) active · \(jobs.count) total")
                    ExportToWebButton()
                    tabs
                    if tab == 0 {
                        ForEach(jobs) { job in
                            NavigationLink(value: job) { JobCardFull(job: job) }.buttonStyle(.plain)
                                .contextMenu {
                                    Button("Edit job", systemImage: "pencil") { editingJob = job }
                                    Button("Delete job", systemImage: "trash", role: .destructive) { context.delete(job) }
                                }
                        }
                        if jobs.isEmpty && !importing {
                            ContentUnavailableView("No jobs yet", systemImage: "hammer", description: Text("Tap + to add a job or import your backup."))
                        }
                    } else {
                        ForEach(estimates) { e in
                            EstimateCard(est: e, edit: { estSheet = EstimateRequest(est: e) }, open: { key in
                                if let j = jobs.first(where: { String($0.created.timeIntervalSince1970) == key }) { openJob = j }
                            })
                        }
                        if estimates.isEmpty {
                            ContentUnavailableView("No estimates yet", systemImage: "doc.text", description: Text("Tap + to build one."))
                        }
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
            .shellAdd { if tab == 1 { estSheet = EstimateRequest(est: nil) } else { asking = true } }
            .sheet(item: $estSheet) { EstimateSheet(est: $0.est) }
            .sheet(item: $editingJob) { EditJobSheet(job: $0) }
            .navigationDestination(item: $openJob) { JobDetailView(job: $0) }
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


// MARK: - Shared form pieces

struct SheetFrame<Content: View>: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("bpDark") private var dark = true
    let title: String
    @ViewBuilder var content: Content
    @State private var pinned: PinnedSave?
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text(title).font(.title.weight(.heavy)).lineLimit(1).minimumScaleFactor(0.6)
                Spacer()
                Button { dismiss() } label: {
                    Image(systemName: "xmark").font(.headline).foregroundStyle(.primary).frame(width: 40, height: 40)
                        .background(Theme.border(dark).opacity(0.6), in: Circle())
                }.buttonStyle(.plain)
            }.padding(.horizontal, 20).padding(.vertical, 14)
            Divider()
            ScrollView { VStack(alignment: .leading, spacing: 18) { content }.padding(20) }
            if let p = pinned {
                Divider()
                PinnedSaveBar(s: p).padding(.horizontal, 20).padding(.vertical, 12)
            }
        }
        .onPreferenceChange(PinnedSaveKey.self) { pinned = $0 }
        .background(Theme.bg(dark))
        #if os(macOS)
        .frame(minWidth: 460, minHeight: 600)
        #endif
    }
}

struct FField: View {
    @AppStorage("bpDark") private var dark = true
    let title: String
    @Binding var text: String
    let prompt: String
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased()).font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
            TextField(prompt, text: $text).textFieldStyle(.plain).font(.title3)
                .padding(.horizontal, 16).frame(height: 54)
                .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))
        }
    }
}

struct FMenu: View {
    @AppStorage("bpDark") private var dark = true
    let title: String
    @Binding var value: String
    let options: [String]
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased()).font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
            Menu {
                ForEach(options, id: \.self) { o in Button(o) { value = o } }
            } label: {
                HStack { Text(value.isEmpty ? "—" : value).font(.title3); Spacer(); Image(systemName: "chevron.down").font(.footnote.weight(.bold)) }
                    .foregroundStyle(.primary).padding(.horizontal, 16).frame(height: 54)
                    .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))
            }.menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
        }
    }
}

struct PinnedSave: Equatable {
    var title: String
    var enabled: Bool
    var action: () -> Void
    static func == (a: PinnedSave, b: PinnedSave) -> Bool { a.title == b.title && a.enabled == b.enabled }
}
struct PinnedSaveKey: PreferenceKey {
    static var defaultValue: PinnedSave? = nil
    static func reduce(value: inout PinnedSave?, nextValue: () -> PinnedSave?) { value = nextValue() ?? value }
}

/// Inside a SheetFrame this doesn't draw in place: it hands itself to the frame, which pins it to the
/// bottom of the sheet so Save is always reachable (long forms, small windows, iPhone with keyboard).
struct FBigButton: View {
    let title: String
    var enabled = true
    let action: () -> Void
    var body: some View {
        Color.clear.frame(height: 0).preference(key: PinnedSaveKey.self, value: PinnedSave(title: title, enabled: enabled, action: action))
    }
}

struct PinnedSaveBar: View {
    let s: PinnedSave
    var body: some View {
        Button(action: s.action) {
            Text(s.title).font(.title3.weight(.bold)).foregroundStyle(.white).frame(maxWidth: .infinity).frame(height: 58)
                .background(Theme.blue.opacity(s.enabled ? 1 : 0.4), in: RoundedRectangle(cornerRadius: 16))
        }.buttonStyle(.plain).disabled(!s.enabled)
    }
}

private func money(_ s: String) -> Double { Double(s.replacingOccurrences(of: ",", with: "").replacingOccurrences(of: "$", with: "")) ?? 0 }

// MARK: - Expense / Receipt

struct ExpenseSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    let job: Job
    @State private var desc = ""
    @State private var amount = ""
    @State private var date = Date()
    @State private var category = "Materials"
    @State private var vendor = ""
    @State private var items = ""
    @State private var pick: [PhotosPickerItem] = []
    @State private var receipt: Data?
    @StateObject private var voice = Dictation()

    var body: some View {
        SheetFrame(title: "New Expense / Receipt") {
            HStack(alignment: .bottom, spacing: 10) {
                FField(title: "Description *", text: $desc, prompt: "What was purchased?")
                Button { if voice.listening { let h = voice.stop(); if !h.isEmpty { desc = h } } else { voice.start() } } label: {
                    Image(systemName: voice.listening ? "stop.fill" : "mic.fill").font(.title2).foregroundStyle(Theme.blue)
                        .frame(width: 60, height: 54).background(Theme.blue.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
                }.buttonStyle(.plain)
            }
            HStack(alignment: .top, spacing: 12) {
                FField(title: "Amount ($) *", text: $amount, prompt: "0.00")
                VStack(alignment: .leading, spacing: 8) {
                    Text("DATE").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                    DatePicker("", selection: $date, displayedComponents: .date).labelsHidden().frame(height: 54)
                }
            }
            FMenu(title: "Category", value: $category, options: ["Materials", "Labor", "Equipment", "Permits", "Fees", "Subcontractor", "Fuel", "Other"])
            FField(title: "Vendor / Supplier", text: $vendor, prompt: "Home Depot, supplier name…")
            Text("RECEIPT / SCAN").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
            PhotosPicker(selection: $pick, matching: .images) {
                Label(receipt == nil ? "Library" : "Receipt added", systemImage: "photo").font(.title3.weight(.bold)).foregroundStyle(.primary)
                    .frame(maxWidth: .infinity).frame(height: 54).background(Theme.blue.opacity(0.10), in: RoundedRectangle(cornerRadius: 14))
            }.buttonStyle(.plain)
            VStack(alignment: .leading, spacing: 8) {
                Text("ITEMS (FOR A MATERIALS SPREADSHEET)").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                TextEditor(text: $items).font(.title3).scrollContentBackground(.hidden).padding(8).frame(height: 90)
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.secondary.opacity(0.5), style: StrokeStyle(lineWidth: 1.5, dash: [5, 4])))
            }
            FBigButton(title: "Save Expense", enabled: !desc.trimmingCharacters(in: .whitespaces).isEmpty && money(amount) > 0) {
                let e = Expense(title: desc.trimmingCharacters(in: .whitespaces), amount: money(amount))
                e.date = date; e.category = category; e.vendor = vendor; e.itemsText = items; e.receipt = receipt
                context.insert(e); e.job = job
                dismiss()
            }
        }
        .onChange(of: pick) { _, new in Task { if let d = try? await new.first?.loadTransferable(type: Data.self) { receipt = d } } }
    }
}

// MARK: - Contractor

struct ContractorSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    let job: Job
    @State private var name = ""
    @State private var trade = "Plumbing"
    @State private var value = ""
    @State private var phone = ""
    @State private var scope = ""
    @State private var hasStart = false
    @State private var start = Date()
    var body: some View {
        SheetFrame(title: "New Contractor") {
            FField(title: "Name *", text: $name, prompt: "Contractor or company")
            FMenu(title: "Trade", value: $trade, options: Trades.all)
            FField(title: "Contract value ($)", text: $value, prompt: "0.00")
            FField(title: "Phone", text: $phone, prompt: "(123)-456-7890")
            FField(title: "Scope of work", text: $scope, prompt: "What they are doing")
            Toggle("Start date", isOn: $hasStart).font(.title3)
            if hasStart { DatePicker("", selection: $start, displayedComponents: .date).labelsHidden() }
            FBigButton(title: "Save Contractor", enabled: !name.trimmingCharacters(in: .whitespaces).isEmpty) {
                let c = Contractor(name: name.trimmingCharacters(in: .whitespaces))
                c.trade = trade; c.value = money(value); c.phone = phone; c.scope = scope; c.startDate = hasStart ? start : nil
                context.insert(c); c.job = job
                dismiss()
            }
        }
    }
}

// MARK: - Invoice

struct InvoiceSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    let job: Job
    @State private var title = ""
    @State private var amount = ""
    @State private var date = Date()
    @State private var status = "Draft"
    @State private var notes = ""
    var body: some View {
        SheetFrame(title: "New Invoice") {
            FField(title: "Title *", text: $title, prompt: "Deposit, Progress billing…")
            HStack(alignment: .top, spacing: 12) {
                FField(title: "Amount ($) *", text: $amount, prompt: "0.00")
                VStack(alignment: .leading, spacing: 8) {
                    Text("DATE").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                    DatePicker("", selection: $date, displayedComponents: .date).labelsHidden().frame(height: 54)
                }
            }
            FMenu(title: "Status", value: $status, options: ["Draft", "Sent", "Paid", "Overdue"])
            FField(title: "Notes", text: $notes, prompt: "Optional")
            FBigButton(title: "Save Invoice", enabled: !title.trimmingCharacters(in: .whitespaces).isEmpty && money(amount) > 0) {
                let i = Invoice(title: title.trimmingCharacters(in: .whitespaces), amount: money(amount))
                i.date = date; i.status = status; i.notes = notes
                context.insert(i); i.job = job
                dismiss()
            }
        }
    }
}

// MARK: - Appointment (also Due Date)

struct ApptRequest: Identifiable { let id = UUID(); let kind: String; let date: Date; let job: Job? }

struct AppointmentSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    let req: ApptRequest
    @State private var title = ""
    @State private var kind = ""
    @State private var date = Date()
    @State private var hasTime = false
    @State private var time = Calendar.current.date(bySettingHour: 9, minute: 0, second: 0, of: Date()) ?? Date()
    @State private var jobName = ""
    @State private var notes = ""
    @StateObject private var voice = Dictation()

    var body: some View {
        SheetFrame(title: "New Appointment") {
            ZStack(alignment: .topTrailing) {
                FField(title: "Title *", text: $title, prompt: "Site visit, inspection, permit review…")
                Button { if voice.listening { let h = voice.stop(); if !h.isEmpty { title = h } } else { voice.start() } } label: {
                    Label(voice.listening ? "Stop" : "Speak", systemImage: "mic.fill").font(.title3.weight(.bold)).foregroundStyle(.white)
                        .padding(.horizontal, 18).frame(height: 44).background(voice.listening ? Theme.red : Theme.blue, in: Capsule())
                }.buttonStyle(.plain).offset(y: -4)
            }
            HStack(alignment: .top, spacing: 12) {
                FMenu(title: "Type", value: $kind, options: Money.appointmentKinds)
                VStack(alignment: .leading, spacing: 8) {
                    Text("DATE *").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                    DatePicker("", selection: $date, displayedComponents: .date).labelsHidden().frame(height: 54)
                }
            }
            Toggle("Time (optional)", isOn: $hasTime).font(.title3)
            if hasTime { DatePicker("", selection: $time, displayedComponents: .hourAndMinute).labelsHidden() }
            FMenu(title: "Job (optional)", value: $jobName, options: ["No job"] + jobs.map(\.name))
            FField(title: "Notes", text: $notes, prompt: "")
            HStack(spacing: 12) {
                Button { dismiss() } label: {
                    Text("Cancel").font(.title3.weight(.bold)).foregroundStyle(.secondary).frame(maxWidth: .infinity).frame(height: 58)
                        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.secondary.opacity(0.5), lineWidth: 1))
                }.buttonStyle(.plain)
                Button { save() } label: {
                    Text("Save").font(.title3.weight(.bold)).foregroundStyle(.white).frame(maxWidth: .infinity).frame(height: 58)
                        .background(Theme.blue.opacity(title.trimmingCharacters(in: .whitespaces).isEmpty ? 0.4 : 1), in: RoundedRectangle(cornerRadius: 16))
                }.buttonStyle(.plain).disabled(title.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .onAppear { kind = req.kind; date = req.date; jobName = req.job?.name ?? "No job" }
    }

    private func save() {
        let a = Appointment(title: title.trimmingCharacters(in: .whitespaces))
        a.kind = kind; a.notes = notes
        let cal = Calendar.current
        let t = hasTime ? cal.dateComponents([.hour, .minute], from: time) : DateComponents(hour: 9, minute: 0)
        a.date = cal.date(bySettingHour: t.hour ?? 9, minute: t.minute ?? 0, second: 0, of: date) ?? date
        context.insert(a)
        a.job = jobs.first { $0.name == jobName }
        dismiss()
    }
}

// MARK: - Add Spaces (rooms / areas by level)

struct AddSpacesSheet: View {
    @Environment(\.modelContext) private var context
    @AppStorage("bpDark") private var dark = true
    let job: Job
    @State private var mode = "Rooms"
    @State private var level = "Level 1"
    @State private var extraLevels: [String] = []
    @State private var custom = ""

    private let rooms = ["Kitchen", "Bathroom", "Basement Bath", "Master Bath", "Half Bath", "Bedroom 1", "Bedroom 2", "Bedroom 3",
                         "Living Room", "Dining Room", "Basement", "Attic", "Garage", "Office", "Foyer", "Hallway", "Stairs",
                         "Laundry", "Utility Room", "Boiler Room", "Closet"]
    private let areas = ["Front Yard", "Backyard", "Driveway", "Porch", "Deck", "Patio", "Roof", "Fence", "Walkway", "Parking Lot", "Garden", "Shed"]
    private var levels: [String] { ["Basement", "Level 1", "Level 2", "Level 3", "Roof", "Outside"] + extraLevels }

    private func existing(_ n: String) -> Space? { (job.spaces ?? []).first { $0.name == n && $0.level == level } }

    private func symbol(_ n: String) -> String { RoomIcon.first(RoomIcon.candidates(for: n, stored: "")) }

    private func toggle(_ n: String) {
        let name = n.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        if let s = existing(name) {
            if (s.punchItems ?? []).isEmpty && (s.photos ?? []).isEmpty { context.delete(s) }
        } else {
            let order = (job.spaces ?? []).filter { $0.level == level }.count
            let s = Space(name: name, level: level, order: order, isExterior: mode == "Areas" || level == "Outside")
            s.symbol = symbol(name)
            s.job = job; context.insert(s)
        }
    }

    var body: some View {
        SheetFrame(title: "Add Spaces") {
            Text("\(job.name) · pick the level, then tap to add (tap again to remove)").foregroundStyle(.secondary)
            HStack(spacing: 12) {
                modeButton("Rooms", "door.left.hand.closed", Theme.purple)
                modeButton("Areas", "mappin.and.ellipse", Theme.purple)
            }
            Text("LEVEL").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
            FlowLayout(spacing: 10) {
                ForEach(levels, id: \.self) { l in
                    Button { level = l } label: {
                        Text(l).font(.title3.weight(.bold)).foregroundStyle(level == l ? Theme.blue : .primary)
                            .padding(.horizontal, 20).frame(height: 52)
                            .background(level == l ? Theme.blue.opacity(0.15) : Color.clear, in: RoundedRectangle(cornerRadius: 16))
                            .overlay(RoundedRectangle(cornerRadius: 16).stroke(level == l ? Theme.blue : Theme.border(dark), lineWidth: 1.5))
                    }.buttonStyle(.plain)
                }
                Button { let n = "Level \(levels.filter { $0.hasPrefix("Level") }.count + 1)"; extraLevels.append(n); level = n } label: {
                    Text("+ Level").font(.title3.weight(.bold)).foregroundStyle(Theme.blue).padding(.horizontal, 20).frame(height: 52)
                        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.blue, style: StrokeStyle(lineWidth: 1.5, dash: [5, 4])))
                }.buttonStyle(.plain)
            }
            Text("\(mode.uppercased()) ON \(level.uppercased())").font(.title3.weight(.heavy)).tracking(1.5).foregroundStyle(Theme.blue)
            FlowLayout(spacing: 10) {
                ForEach(mode == "Rooms" ? rooms : areas, id: \.self) { r in
                    let on = existing(r) != nil
                    Button { toggle(r) } label: {
                        HStack(spacing: 8) {
                            Image(systemName: symbol(r))
                            if on { Image(systemName: "checkmark") } else { Text("+") }
                            Text(r)
                        }.font(.title3.weight(.bold)).foregroundStyle(on ? Theme.blue : .primary)
                        .padding(.horizontal, 18).frame(height: 52)
                        .background(on ? Theme.blue.opacity(0.15) : Color.clear, in: Capsule())
                        .overlay(Capsule().stroke(on ? Theme.blue : Theme.border(dark), lineWidth: 1.5))
                    }.buttonStyle(.plain)
                }
            }
            HStack(spacing: 12) {
                TextField("Type your own on \(level)…", text: $custom).textFieldStyle(.plain).font(.title3)
                    .padding(.horizontal, 14).frame(height: 54)
                    .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))
                    .onSubmit { toggle(custom); custom = "" }
                Button("Add") { toggle(custom); custom = "" }.font(.title3.weight(.bold)).foregroundStyle(.white)
                    .padding(.horizontal, 22).frame(height: 54).background(Theme.blue, in: RoundedRectangle(cornerRadius: 14)).buttonStyle(.plain)
            }
        }
    }

    private func modeButton(_ t: String, _ sym: String, _ c: Color) -> some View {
        Button { mode = t } label: {
            Label(t, systemImage: sym).font(.title2.weight(.bold)).foregroundStyle(mode == t ? c : .secondary)
                .frame(maxWidth: .infinity).frame(height: 70)
                .background(mode == t ? c.opacity(0.15) : Color.clear, in: RoundedRectangle(cornerRadius: 18))
                .overlay(RoundedRectangle(cornerRadius: 18).stroke(mode == t ? c : Theme.border(dark), lineWidth: 2))
        }.buttonStyle(.plain)
    }
}


// MARK: - "Add to this job" picker (full list; native alerts clip long lists on Mac)
struct AddPickerSheet: View {
    let pick: (String) -> Void
    private let items: [(String, String)] = [
        ("Space", "square.grid.2x2"), ("Expense", "receipt"), ("Contractor", "person.badge.plus"),
        ("Change order", "arrow.triangle.2.circlepath"), ("Invoice", "doc.text"), ("Permit", "checkmark.seal"),
        ("Delivery", "shippingbox"), ("Daily report", "doc.plaintext"), ("Appointment", "calendar.badge.plus"),
        ("Note", "note.text"), ("Shopping item", "cart")]
    var body: some View {
        SheetFrame(title: "Add to this job") {
            VStack(spacing: 10) {
                ForEach(items, id: \.0) { it in
                    Button { pick(it.0) } label: {
                        HStack(spacing: 14) {
                            Image(systemName: it.1).font(.title3).frame(width: 30)
                            Text(it.0).font(.headline)
                            Spacer()
                            Image(systemName: "chevron.right").font(.footnote).foregroundStyle(.secondary)
                        }
                        .padding(.horizontal, 16).frame(height: 54)
                        .background(Color.gray.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
                    }.buttonStyle(.plain)
                }
            }.padding(.horizontal, 20).padding(.bottom, 20)
        }
    }
}


// MARK: - Finance "+" (pick job, then what to add)
struct FinanceAddSheet: View {
    let jobs: [Job]
    let initial: Job?
    let pick: (Job, String) -> Void
    @State private var jobName = ""
    private let items: [(String, String)] = [("Expense", "receipt"), ("Contractor", "person.badge.plus"), ("Invoice", "doc.text"), ("Change order", "arrow.triangle.2.circlepath"), ("Permit", "checkmark.seal"), ("Delivery", "shippingbox")]
    private var job: Job? { jobs.first { $0.name == jobName } ?? initial ?? jobs.first }
    var body: some View {
        SheetFrame(title: "Add to Finance") {
            FMenu(title: "Job", value: $jobName, options: jobs.map(\.name))
            VStack(spacing: 10) {
                ForEach(items, id: \.0) { it in
                    Button { if let j = job { pick(j, it.0) } } label: {
                        HStack(spacing: 14) {
                            Image(systemName: it.1).font(.title3).frame(width: 30)
                            Text(it.0).font(.headline)
                            Spacer()
                            Image(systemName: "chevron.right").font(.footnote).foregroundStyle(.secondary)
                        }
                        .padding(.horizontal, 16).frame(height: 54)
                        .background(Color.gray.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
                    }.buttonStyle(.plain)
                }
            }
        }
        .onAppear { if jobName.isEmpty { jobName = (initial ?? jobs.first)?.name ?? "" } }
    }
}


// MARK: - Change order / Permit / Delivery forms

struct ChangeOrderSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    let job: Job
    @State private var title = ""
    @State private var details = ""
    @State private var amount = ""
    @State private var days = ""
    @State private var status = "Draft"
    @State private var reason = "Owner request"
    private var number: String { String(format: "CO-%03d", (job.changeOrders ?? []).count + 1) }
    var body: some View {
        SheetFrame(title: "New \(number)") {
            FField(title: "Title *", text: $title, prompt: "What's changing?")
            FField(title: "Details", text: $details, prompt: "Describe the change")
            HStack(alignment: .top, spacing: 12) {
                FField(title: "Amount ($)", text: $amount, prompt: "0.00 (negative = credit)")
                FField(title: "Days added", text: $days, prompt: "0")
            }
            FMenu(title: "Status", value: $status, options: ["Draft", "Submitted", "Approved", "Rejected", "Void"])
            FMenu(title: "Reason", value: $reason, options: ["Owner request", "Field condition", "Design change", "Code / inspector", "Hidden condition", "Scope clarification", "Other"])
            FBigButton(title: "Save Change Order", enabled: !title.trimmingCharacters(in: .whitespaces).isEmpty) {
                let c = ChangeOrder(number: number)
                c.title = title.trimmingCharacters(in: .whitespaces); c.details = details
                c.amount = money(amount); c.daysAdded = Int(days) ?? 0; c.status = status; c.reason = reason
                if status == "Approved" { c.approvedAt = Date() }
                context.insert(c); c.job = job
                dismiss()
            }
        }
    }
}

struct PermitSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    let job: Job
    @State private var trade = "General"
    @State private var number = ""
    @State private var cost = ""
    @State private var status = "Active"
    @State private var issue = Date()
    @State private var expires = Calendar.current.date(byAdding: .month, value: 6, to: Date()) ?? Date()
    @State private var notes = ""
    var body: some View {
        SheetFrame(title: "New Permit") {
            FMenu(title: "Trade", value: $trade, options: ["General", "Electrical", "Plumbing", "HVAC", "Framing", "Roofing", "Masonry", "Building", "Other"])
            FField(title: "Permit number", text: $number, prompt: "e.g. B-2026-0142")
            HStack(alignment: .top, spacing: 12) {
                FField(title: "Cost ($)", text: $cost, prompt: "0.00")
                FMenu(title: "Status", value: $status, options: ["Active", "Pending", "Closed"])
            }
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("ISSUE DATE").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                    DatePicker("", selection: $issue, displayedComponents: .date).labelsHidden()
                }
                VStack(alignment: .leading, spacing: 8) {
                    Text("EXPIRATION *").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                    DatePicker("", selection: $expires, displayedComponents: .date).labelsHidden()
                }
            }
            FField(title: "Notes", text: $notes, prompt: "Optional")
            FBigButton(title: "Save Permit") {
                let p = Permit(trade: trade)
                p.number = number; p.cost = money(cost); p.status = status
                p.issueDate = issue; p.expirationDate = expires; p.notes = notes
                context.insert(p); p.job = job
                dismiss()
            }
        }
    }
}

struct DeliverySheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    let job: Job
    @State private var what = ""
    @State private var supplier = ""
    @State private var date = Date()
    @State private var window = ""
    @State private var po = ""
    @State private var amount = ""
    @State private var status = "Scheduled"
    @State private var notes = ""
    var body: some View {
        SheetFrame(title: "Schedule Delivery") {
            FField(title: "What's coming *", text: $what, prompt: "Lumber, tile, fixtures…")
            FField(title: "Supplier *", text: $supplier, prompt: "Home Depot, supplier name…")
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("DELIVERY DATE *").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                    DatePicker("", selection: $date, displayedComponents: .date).labelsHidden().frame(height: 54)
                }
                FField(title: "Time window", text: $window, prompt: "8–10 AM")
            }
            HStack(alignment: .top, spacing: 12) {
                FField(title: "PO / Order #", text: $po, prompt: "Optional")
                FField(title: "Amount ($)", text: $amount, prompt: "0.00")
            }
            Text("Leave the amount at 0 if the ticket hasn't come yet — fill it in when you mark it received.").font(.callout).foregroundStyle(.secondary)
            FMenu(title: "Status", value: $status, options: ["Scheduled", "Delivered", "Partial", "Backordered"])
            FField(title: "Notes", text: $notes, prompt: "Optional")
            FBigButton(title: "Save Delivery", enabled: !what.trimmingCharacters(in: .whitespaces).isEmpty && !supplier.trimmingCharacters(in: .whitespaces).isEmpty) {
                let e = Expense(title: what.trimmingCharacters(in: .whitespaces), amount: money(amount))
                e.vendor = supplier; e.category = "Delivery"; e.date = date
                e.deliveryStatus = status; e.poNumber = po; e.timeWindow = window
                context.insert(e); e.job = job
                let a = Appointment(title: "🚚 " + e.title)
                a.kind = "Delivery"; a.date = date
                a.notes = [supplier, window, po.isEmpty ? "" : "PO " + po, notes].filter { !$0.isEmpty }.joined(separator: " · ")
                context.insert(a); a.job = job
                dismiss()
            }
        }
    }
}


// MARK: - Estimates UI

struct EstimateRequest: Identifiable { let id = UUID(); let est: Estimate? }

struct EstimateCard: View {
    @Environment(\.modelContext) private var context
    @Environment(\.openURL) private var openURL
    @AppStorage("bpDark") private var dark = true
    let est: Estimate
    let edit: () -> Void
    let open: (String) -> Void
    @State private var confirmDelete = false

    private var statusColor: Color {
        switch est.status { case "Sent": return Theme.lightBlue; case "Accepted": return Theme.blue; case "Declined": return Theme.red; default: return .secondary }
    }
    private func usd2(_ v: Double) -> String { v.formatted(.currency(code: "USD")) }

    var body: some View {
        CardBox {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(est.title).font(.title2.weight(.bold)).lineLimit(2)
                        if !est.client.isEmpty { Label(est.client, systemImage: "person").font(.callout).foregroundStyle(.secondary) }
                    }
                    Spacer()
                    Text(est.status).font(.callout.weight(.bold)).foregroundStyle(statusColor)
                        .padding(.horizontal, 12).padding(.vertical, 5)
                        .overlay(Capsule().stroke(statusColor.opacity(0.5)))
                }
                Text(usd2(est.total)).font(.system(size: 30, weight: .heavy)).foregroundStyle(Theme.blue)
                HStack(spacing: 8) {
                    pill("Edit", "pencil", Theme.card(dark), .primary, action: edit)
                    pill(nil, "envelope", Theme.card(dark), Theme.blue, action: email)
                    if est.convertedJobKey.isEmpty {
                        pill("Convert to Job", nil, Theme.orange, .white, grow: true, action: convert)
                    } else {
                        pill("View Job →", nil, Theme.blue, .white, grow: true) { open(est.convertedJobKey) }
                    }
                    pill(nil, "trash", Theme.card(dark), .secondary) { confirmDelete = true }
                }
            }
        }
        .confirmationDialog("Delete this estimate?", isPresented: $confirmDelete) {
            Button("Delete", role: .destructive) { context.delete(est) }
        }
    }

    private func pill(_ title: String?, _ symbol: String?, _ bg: Color, _ fg: Color, grow: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if let symbol { Image(systemName: symbol) }
                if let title { Text(title).font(.headline.weight(.bold)) }
            }
            .foregroundStyle(fg).padding(.horizontal, 14).frame(maxWidth: grow || title != nil ? .infinity : nil).frame(height: 46)
            .background(bg, in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
        }.buttonStyle(.plain)
    }

    private func convert() {
        let j = Job(name: est.title)
        j.client = est.client; j.clientEmail = est.clientEmail; j.contract = est.total; j.status = "Pending"
        context.insert(j)
        est.convertedJobKey = String(j.created.timeIntervalSince1970)
        est.status = "Accepted"
        open(est.convertedJobKey)
    }

    private func email() {
        let money = { (v: Double) in v.formatted(.currency(code: "USD")) }
        let lines = est.lines.filter { !$0.desc.isEmpty || $0.price != 0 }
            .map { "  • \($0.desc.isEmpty ? "Item" : $0.desc)  x\(Int($0.qty))  \(money($0.price))" }.joined(separator: "\n")
        let body = "Hi\(est.client.isEmpty ? "" : " " + est.client),\n\nHere is the estimate for \(est.title):\n\n" + (lines.isEmpty ? "" : lines + "\n\n")
            + "Total: \(money(est.total))\n" + (est.notes.isEmpty ? "" : "\n" + est.notes + "\n") + "\nThanks,\n"
        var comps = URLComponents(); comps.scheme = "mailto"; comps.path = est.clientEmail
        comps.queryItems = [URLQueryItem(name: "subject", value: "Estimate: \(est.title) – \(money(est.total))"), URLQueryItem(name: "body", value: body)]
        if let u = comps.url { openURL(u) }
    }
}

struct EstimateSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @AppStorage("bpDark") private var dark = true
    let est: Estimate?
    @State private var title = ""
    @State private var client = ""
    @State private var email = ""
    @State private var status = "Draft"
    @State private var notes = ""
    @State private var lines: [EstimateLine] = [EstimateLine()]
    @State private var loaded = false

    private var total: Double { lines.reduce(0) { $0 + $1.qty * $1.price } }

    var body: some View {
        SheetFrame(title: est == nil ? "New Estimate" : "Edit Estimate") {
            FField(title: "Title *", text: $title, prompt: "e.g. Kitchen Remodel")
            FField(title: "Client", text: $client, prompt: "")
            FField(title: "Client Email", text: $email, prompt: "client@example.com")
            FMenu(title: "Status", value: $status, options: ["Draft", "Sent", "Accepted", "Declined"])
            Text("LINE ITEMS").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
            ForEach($lines) { $l in
                HStack(spacing: 8) {
                    TextField("Description", text: $l.desc).textFieldStyle(.plain).padding(12).frame(height: 48)
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 10))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border(dark)))
                    TextField("Qty", value: $l.qty, format: .number).textFieldStyle(.plain).padding(12).frame(width: 70, height: 48)
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 10))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border(dark)))
                    TextField("Price", value: $l.price, format: .number).textFieldStyle(.plain).padding(12).frame(width: 100, height: 48)
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 10))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border(dark)))
                    Button { removeLine(l.id) } label: { Image(systemName: "xmark").foregroundStyle(.secondary) }.buttonStyle(.plain)
                }
            }
            Button { lines.append(EstimateLine()) } label: {
                Text("+ Add Line Item").font(.headline.weight(.bold)).foregroundStyle(.secondary).frame(maxWidth: .infinity, minHeight: 48)
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(style: StrokeStyle(lineWidth: 1.5, dash: [6])).foregroundStyle(.secondary))
            }.buttonStyle(.plain)
            HStack {
                Text("Total").font(.headline).foregroundStyle(.secondary)
                Spacer()
                Text(total.formatted(.currency(code: "USD"))).font(.title.weight(.heavy)).foregroundStyle(Theme.blue)
            }
            .padding(16).background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
            FField(title: "Notes", text: $notes, prompt: "")
            FBigButton(title: "Save Estimate", enabled: !title.trimmingCharacters(in: .whitespaces).isEmpty) { save() }
        }
        .onAppear {
            guard !loaded, let e = est else { return }
            loaded = true
            title = e.title; client = e.client; email = e.clientEmail; status = e.status; notes = e.notes
            lines = e.lines.isEmpty ? [EstimateLine()] : e.lines
        }
    }

    private func removeLine(_ id: UUID) {
        if lines.count <= 1 { lines = [EstimateLine()] } else { lines.removeAll { $0.id == id } }
    }

    private func save() {
        let e = est ?? Estimate(title: "")
        e.title = title.trimmingCharacters(in: .whitespaces); e.client = client; e.clientEmail = email
        e.status = status; e.notes = notes; e.updated = Date()
        e.lines = lines.filter { !$0.desc.isEmpty || $0.price != 0 }
        if est == nil { context.insert(e) }
        dismiss()
    }
}


// MARK: - Edit job

struct EditJobSheet: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("bpDark") private var dark = true
    @Bindable var job: Job
    @State private var name = ""
    @State private var address = ""
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
    @State private var loaded = false

    var body: some View {
        SheetFrame(title: "Edit Job") {
            FField(title: "Job name *", text: $name, prompt: "e.g. Smith Kitchen Reno")
            FField(title: "Job address", text: $address, prompt: "Street, City, State Zip")
            FField(title: "Client name", text: $client, prompt: "Client name")
            FField(title: "Client email", text: $email, prompt: "client@example.com")
            FField(title: "Client cell", text: $cell, prompt: "(123)-456-7890")
            FField(title: "Contract value ($)", text: $contract, prompt: "0.00")
            FMenu(title: "Status", value: $status, options: ["Active", "Pending", "On hold", "Complete"])
            Toggle("Start date", isOn: $hasStart).font(.title3)
            if hasStart { DatePicker("", selection: $start, displayedComponents: .date).labelsHidden() }
            Toggle("Completion date", isOn: $hasEnd).font(.title3)
            if hasEnd { DatePicker("", selection: $end, displayedComponents: .date).labelsHidden() }
            VStack(alignment: .leading, spacing: 8) {
                Text("NOTES").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                TextEditor(text: $notes).font(.title3).scrollContentBackground(.hidden).padding(8).frame(height: 110)
                    .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))
            }
            FBigButton(title: "Save Changes", enabled: !name.trimmingCharacters(in: .whitespaces).isEmpty) { save() }
        }
        .onAppear {
            guard !loaded else { return }
            loaded = true
            name = job.name; address = job.address; client = job.client; email = job.clientEmail; cell = job.clientPhone
            contract = job.contract == 0 ? "" : String(format: "%g", job.contract)
            status = job.status.isEmpty ? (job.isActive ? "Active" : "Complete") : job.status
            if let s = job.startDate { hasStart = true; start = s }
            if let e = job.completionDate { hasEnd = true; end = e }
            notes = job.jobNotes
        }
    }

    private func save() {
        job.name = name.trimmingCharacters(in: .whitespaces)
        job.address = address; job.client = client; job.clientEmail = email; job.clientPhone = cell
        job.contract = Double(contract.replacingOccurrences(of: ",", with: "").replacingOccurrences(of: "$", with: "")) ?? 0
        job.status = status; job.isActive = status != "Complete"
        job.startDate = hasStart ? start : nil; job.completionDate = hasEnd ? end : nil
        job.jobNotes = notes
        dismiss()
    }
}

// MARK: - Multi-line field

struct FArea: View {
    @AppStorage("bpDark") private var dark = true
    let title: String
    @Binding var text: String
    let prompt: String
    var height: CGFloat = 90
    var tint: Color = .secondary
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased()).font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(tint)
            ZStack(alignment: .topLeading) {
                TextEditor(text: $text).font(.title3).scrollContentBackground(.hidden).padding(8).frame(height: height)
                if text.isEmpty {
                    Text(prompt).font(.title3).foregroundStyle(.secondary.opacity(0.7))
                        .padding(.horizontal, 13).padding(.top, 16).allowsHitTesting(false)
                }
            }
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))
        }
    }
}

// MARK: - Shopping item (Qty | Item | Cost)

struct ShoppingSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @AppStorage("bpDark") private var dark = true
    let job: Job
    @State private var qty = "1"
    @State private var text = ""
    @State private var price = ""
    @State private var added = 0

    private var ready: Bool { !text.trimmingCharacters(in: .whitespaces).isEmpty }
    private func save() {
        let it = ShoppingItem(text: text.trimmingCharacters(in: .whitespaces))
        let q = money(qty); it.qty = q > 0 ? q : 1; it.price = money(price)
        context.insert(it); it.job = job
        added += 1
    }

    var body: some View {
        SheetFrame(title: "Add item") {
            HStack(alignment: .top, spacing: 10) {
                FField(title: "Qty", text: $qty, prompt: "1").frame(width: 90)
                FField(title: "Item", text: $text, prompt: "1/2\" PEX elbow")
                FField(title: "Cost $", text: $price, prompt: "0.00").frame(width: 110)
            }
            Text("Cost is per item. Tap the item afterwards to add store, notes and more.").font(.callout).foregroundStyle(.secondary)
            if added > 0 { Label("\(added) added", systemImage: "checkmark.circle.fill").foregroundStyle(Theme.green).font(.headline) }
            Button {
                guard ready else { return }
                save(); text = ""; price = ""; qty = "1"
            } label: {
                Text("Add + next").font(.title3.weight(.bold)).foregroundStyle(ready ? Theme.blue : .secondary)
                    .frame(maxWidth: .infinity).frame(height: 54)
                    .background(Theme.blue.opacity(0.10), in: RoundedRectangle(cornerRadius: 14))
            }.buttonStyle(.plain).disabled(!ready)
            FBigButton(title: "Add item", enabled: ready) { save(); dismiss() }
        }
    }
}

// MARK: - Note

struct NoteSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    let job: Job
    @State private var title = ""
    @State private var text = ""
    @StateObject private var voice = Dictation()

    private var ready: Bool { !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    var body: some View {
        SheetFrame(title: "New Note") {
            Text(job.name).foregroundStyle(.secondary)
            FField(title: "Title", text: $title, prompt: "Optional — uses the first line if blank")
            HStack(alignment: .bottom, spacing: 10) {
                FArea(title: "Note", text: $text, prompt: "What do you want to remember?", height: 220)
                Button { if voice.listening { let h = voice.stop(); if !h.isEmpty { text += (text.isEmpty ? "" : "\n") + h } } else { voice.start() } } label: {
                    Image(systemName: voice.listening ? "stop.fill" : "mic.fill").font(.title2).foregroundStyle(Theme.blue)
                        .frame(width: 60, height: 54).background(Theme.blue.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
                }.buttonStyle(.plain)
            }
            FBigButton(title: "Save Note", enabled: ready) {
                let body = text.trimmingCharacters(in: .whitespacesAndNewlines)
                var t = title.trimmingCharacters(in: .whitespaces)
                if t.isEmpty {
                    let first = body.components(separatedBy: .newlines).first ?? "Note"
                    if first.count <= 40 { t = first }
                    else {
                        let cut = String(first.prefix(40))
                        t = (cut.lastIndex(of: " ").map { String(cut[..<$0]) } ?? cut) + "…"
                    }
                }
                let n = JobNote(title: t); n.text = body
                context.insert(n); n.job = job
                dismiss()
            }
        }
    }
}

// MARK: - Daily Log (one per job per day)

struct DailyLogSheet: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @AppStorage("bpDark") private var dark = true
    let job: Job
    @State private var day = Calendar.current.startOfDay(for: Date())
    @State private var completed = ""
    @State private var workers = "1"
    @State private var hours = ""
    @State private var weather = ""
    @State private var incomplete = ""
    @State private var visitors = ""
    @State private var safety = ""
    @State private var tomorrow = ""
    @State private var clientNotes = ""
    @State private var loaded = false

    private var cal: Calendar { .current }
    private func same(_ d: Date) -> Bool { cal.isDate(d, inSameDayAs: day) }
    private var isToday: Bool { cal.isDateInToday(day) }
    private var existing: DailyReport? { (job.reports ?? []).filter { same($0.date) }.first }

    // What the app recorded that day
    private var photos: Int { (job.photos ?? []).filter { same($0.created) }.count }
    private var doneItems: [PunchItem] { (job.punchItems ?? []).filter { $0.done && $0.completed.map(same) == true } }
    private var addedItems: Int { (job.punchItems ?? []).filter { same($0.created) }.count }
    private var clockHours: Double { ((job.timeEntries ?? []).filter { same($0.clockIn) }.reduce(0) { $0 + $1.hours } * 10).rounded() / 10 }
    private var dayExpenses: [Expense] { (job.expenses ?? []).filter { same($0.date) && $0.deliveryStatus.isEmpty } }
    private var dayDeliveries: Int { (job.expenses ?? []).filter { same($0.date) && !$0.deliveryStatus.isEmpty }.count }
    private var dayAppts: [Appointment] { (job.appointments ?? []).filter { same($0.date) } }
    private var dayCOs: Int { (job.changeOrders ?? []).filter { same($0.date) }.count }
    private var pct: Int { job.percent }

    private func usd(_ v: Double) -> String { v.formatted(.currency(code: "USD")) }
    private func num(_ v: Double) -> String { v == v.rounded() ? String(Int(v)) : String(v) }

    private func load() {
        if let r = existing {
            completed = r.completed; workers = String(r.workers); hours = r.hours; weather = r.weather
            incomplete = r.incomplete; visitors = r.visitors; safety = r.safety; tomorrow = r.tomorrow; clientNotes = r.clientNotes
        } else {
            completed = ""; workers = "1"; hours = clockHours > 0 ? num(clockHours) : ""; weather = ""
            incomplete = ""; visitors = ""; safety = ""; tomorrow = ""; clientNotes = ""
        }
    }
    private func step(_ n: Int) {
        guard let d = cal.date(byAdding: .day, value: n, to: day), d <= cal.startOfDay(for: Date()) else { return }
        day = d; load()
    }
    private func fill() {
        let lines = doneItems.map { "• " + (($0.space?.name).map { $0 + ": " } ?? "") + $0.text }
        let add = lines.filter { !completed.contains($0) }
        guard !add.isEmpty else { return }
        completed = (completed.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "" : completed.trimmingCharacters(in: .whitespacesAndNewlines) + "\n") + add.joined(separator: "\n")
    }
    private func save() {
        let r: DailyReport
        if let e = existing { r = e } else {
            r = DailyReport(number: String(format: "DPR-%03d", (job.reports ?? []).count + 1))
            r.date = day; context.insert(r); r.job = job
        }
        r.completed = completed.trimmingCharacters(in: .whitespacesAndNewlines)
        r.workers = Int(workers) ?? 0
        r.hours = hours.trimmingCharacters(in: .whitespaces)
        r.weather = weather.trimmingCharacters(in: .whitespaces)
        r.incomplete = incomplete.trimmingCharacters(in: .whitespacesAndNewlines)
        r.visitors = visitors.trimmingCharacters(in: .whitespacesAndNewlines)
        r.safety = safety.trimmingCharacters(in: .whitespacesAndNewlines)
        r.tomorrow = tomorrow.trimmingCharacters(in: .whitespacesAndNewlines)
        r.clientNotes = clientNotes.trimmingCharacters(in: .whitespacesAndNewlines)
        r.progress = pct
        dismiss()
    }

    private func fact(_ label: String, _ value: String, _ color: Color? = nil) -> some View {
        HStack { Text(label).foregroundStyle(.secondary); Spacer(); Text(value).fontWeight(.heavy).foregroundStyle(color ?? .primary).multilineTextAlignment(.trailing) }
            .font(.body).padding(.vertical, 8)
            .overlay(alignment: .bottom) { Divider() }
    }

    var body: some View {
        SheetFrame(title: "Daily Log") {
            Text(job.name).font(.title3.weight(.heavy))
            HStack(spacing: 10) {
                Button { step(-1) } label: { Image(systemName: "chevron.left").font(.title2.weight(.bold)).frame(width: 54, height: 50)
                    .background(Theme.border(dark).opacity(0.5), in: RoundedRectangle(cornerRadius: 12)) }.buttonStyle(.plain)
                HStack(spacing: 6) {
                    Text((isToday ? "Today · " : cal.isDateInYesterday(day) ? "Yesterday · " : "") + day.formatted(.dateTime.weekday(.abbreviated).month(.abbreviated).day().year()))
                        .font(.headline.weight(.heavy)).lineLimit(1).minimumScaleFactor(0.7)
                    if existing != nil { Image(systemName: "checkmark").foregroundStyle(Theme.green).font(.headline.weight(.heavy)) }
                }.frame(maxWidth: .infinity)
                Button { step(1) } label: { Image(systemName: "chevron.right").font(.title2.weight(.bold)).frame(width: 54, height: 50)
                    .background(Theme.border(dark).opacity(0.5), in: RoundedRectangle(cornerRadius: 12)) }
                    .buttonStyle(.plain).opacity(isToday ? 0.35 : 1).disabled(isToday)
            }
            if !isToday {
                Button { day = cal.startOfDay(for: Date()); load() } label: {
                    Text("Jump to today").font(.headline).foregroundStyle(Theme.blue).frame(maxWidth: .infinity).frame(height: 42)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark), lineWidth: 1))
                }.buttonStyle(.plain)
            }
            VStack(alignment: .leading, spacing: 0) {
                Text("WHAT THE APP RECORDED THIS DAY").font(.subheadline.weight(.heavy)).tracking(1).foregroundStyle(.secondary).padding(.bottom, 4)
                fact("Photos", String(photos), photos > 0 ? Theme.blue : nil)
                fact("Checklist finished", String(doneItems.count), doneItems.isEmpty ? nil : Theme.green)
                fact("Checklist added", String(addedItems))
                if clockHours > 0 { fact("Time clock", num(clockHours) + " hr") }
                if !dayExpenses.isEmpty { fact("Expenses", "\(dayExpenses.count) · " + usd(dayExpenses.reduce(0) { $0 + $1.amount })) }
                if dayDeliveries > 0 { fact("Deliveries", String(dayDeliveries), Theme.orange) }
                if !dayAppts.isEmpty { fact("Appointments", dayAppts.map(\.title).joined(separator: ", ")) }
                if dayCOs > 0 { fact("Change orders", String(dayCOs), Theme.purple) }
                if !doneItems.isEmpty {
                    Button { fill() } label: {
                        Text("Fill \"Work done\" from \(doneItems.count) finished item\(doneItems.count == 1 ? "" : "s")").font(.headline.weight(.bold))
                            .foregroundStyle(Theme.green).frame(maxWidth: .infinity).frame(height: 48)
                            .background(Theme.green.opacity(0.14), in: RoundedRectangle(cornerRadius: 12))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.green, lineWidth: 1.5))
                    }.buttonStyle(.plain).padding(.top, 10)
                }
            }
            .padding(14).background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark), lineWidth: 1))

            FArea(title: "Work done", text: $completed, prompt: "What got done today", height: 120)
            HStack(alignment: .top, spacing: 12) {
                FField(title: "Crew on site", text: $workers, prompt: "1")
                FField(title: "Hours worked", text: $hours, prompt: clockHours > 0 ? num(clockHours) : "8")
            }
            FField(title: "Weather", text: $weather, prompt: "Sunny 72°")
            FArea(title: "Problems / delays", text: $incomplete, prompt: "Waiting on parts, rain, access…")
            FArea(title: "Visitors & inspections", text: $visitors, prompt: "Inspector, client walk-through, supplier…")
            FArea(title: "Safety", text: $safety, prompt: "Anything to note")
            FArea(title: "Tomorrow's plan", text: $tomorrow, prompt: "What's next")
            FArea(title: "Note for the client", text: $clientNotes, prompt: "Goes in what you send the client", tint: Theme.orange)
            Text("Hours, visitors and problems stay in your log. The client gets the work done, what's still open, tomorrow's plan, your note and the day's photos.")
                .font(.callout).foregroundStyle(.secondary)
            FBigButton(title: existing == nil ? "Save log" : "Save changes", enabled: true) { save() }
        }
        .onAppear { if !loaded { loaded = true; load() } }
    }
}


/// Swipe a row left to reveal Delete (full swipe deletes). Works inside ScrollView/VStack rows, where List's swipeActions can't.
struct SwipeDelete: ViewModifier {
    let onDelete: () -> Void
    @State private var offset: CGFloat = 0
    @State private var open = false
    private let reveal: CGFloat = 96

    func body(content: Content) -> some View {
        ZStack(alignment: .trailing) {
            if offset < 0 {
                Button { withAnimation(.easeOut(duration: 0.2)) { offset = 0; open = false }; onDelete() } label: {
                    Label("Delete", systemImage: "trash.fill").labelStyle(.titleAndIcon).font(.headline.weight(.bold)).foregroundStyle(.white)
                        .frame(width: max(0, -offset), alignment: .center).frame(maxHeight: .infinity)
                        .background(Color.red, in: RoundedRectangle(cornerRadius: 18))
                }.buttonStyle(.plain)
            }
            content
                .offset(x: offset)
                .simultaneousGesture(
                    DragGesture(minimumDistance: 18)
                        .onChanged { v in
                            guard abs(v.translation.width) > abs(v.translation.height) else { return }
                            let base: CGFloat = open ? -reveal : 0
                            offset = min(0, max(-320, base + v.translation.width))
                        }
                        .onEnded { v in
                            guard abs(v.translation.width) > abs(v.translation.height) else { return }
                            withAnimation(.easeOut(duration: 0.2)) {
                                if offset < -240 { offset = 0; open = false; onDelete() }
                                else if offset < -reveal / 2 { offset = -reveal; open = true }
                                else { offset = 0; open = false }
                            }
                        }
                )
        }
    }
}

extension View {
    func swipeToDelete(_ action: @escaping () -> Void) -> some View { modifier(SwipeDelete(onDelete: action)) }
}
