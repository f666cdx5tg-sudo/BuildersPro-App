import SwiftUI
import SwiftData

// MARK: - Look (same colors as the web field app)

enum Theme {
    static let blue = Color(red: 0.039, green: 0.518, blue: 1.0)        // #0A84FF
    static let orange = Color(red: 1.0, green: 0.667, blue: 0.2)        // #FFAA33
    static func bg(_ dark: Bool) -> Color { dark ? Color(red: 0.059, green: 0.059, blue: 0.059) : Color(red: 0.949, green: 0.969, blue: 1.0) }
    static func card(_ dark: Bool) -> Color { dark ? Color(red: 0.102, green: 0.102, blue: 0.102) : .white }
    static func border(_ dark: Bool) -> Color { dark ? Color(red: 0.165, green: 0.165, blue: 0.165) : Color(red: 0.878, green: 0.878, blue: 0.878) }
}

private struct OpenMenuKey: EnvironmentKey { static let defaultValue: () -> Void = {} }
extension EnvironmentValues { var openMenu: () -> Void { get { self[OpenMenuKey.self] } set { self[OpenMenuKey.self] = newValue } } }

/// The ☰ button that opens the slide-out menu (top-left on every main screen, like the web app).
struct MenuButton: View {
    @Environment(\.openMenu) private var openMenu
    var body: some View {
        Button { openMenu() } label: { Image(systemName: "line.3.horizontal").font(.title3.bold()) }
    }
}

enum AppScreen: String, CaseIterable, Identifiable {
    case home = "Home", jobs = "Jobs", punch = "Punch", photos = "Photos", money = "Money", search = "Search", calendar = "Calendar"
    var id: String { rawValue }
    var symbol: String {
        switch self {
        case .home: return "house"
        case .jobs: return "briefcase"
        case .punch: return "checkmark.square"
        case .photos: return "camera"
        case .money: return "dollarsign"
        case .search: return "magnifyingglass"
        case .calendar: return "calendar"
        }
    }
}

// MARK: - Root: slide-out menu + the screens

struct RootShell: View {
    @AppStorage("bpDark") private var dark = true
    @AppStorage("bpTextSize") private var textSize = 0          // 0 Normal, 1 Large, 2 Extra large
    @State private var screen: AppScreen = .home
    @State private var menu = false

    private var dynamicSize: DynamicTypeSize { [DynamicTypeSize.large, .xLarge, .xxxLarge][min(max(textSize, 0), 2)] }
    private let sizeNames = ["Normal", "Large", "Extra large"]

    var body: some View {
        ZStack(alignment: .leading) {
            Group {
                switch screen {
                case .home: HomeView(go: { screen = $0 })
                case .jobs: JobsView()
                case .punch: AllPunchView()
                case .photos: AllPhotosView()
                case .money: AllMoneyView()
                case .search: SearchView()
                case .calendar: AllCalendarView()
                }
            }
            .environment(\.openMenu, { withAnimation(.easeOut(duration: 0.25)) { menu = true } })

            if menu {
                Color.black.opacity(0.5).ignoresSafeArea()
                    .onTapGesture { withAnimation(.easeOut(duration: 0.25)) { menu = false } }
                    .transition(.opacity)
                drawer.transition(.move(edge: .leading))
            }
        }
        .tint(Theme.blue)
        .preferredColorScheme(dark ? .dark : .light)
        .dynamicTypeSize(dynamicSize)
    }

    private var drawer: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("BuildersPro").font(.title2.weight(.black))
                Spacer()
                Button { withAnimation(.easeOut(duration: 0.25)) { menu = false } } label: {
                    Image(systemName: "xmark").font(.headline).frame(width: 42, height: 42)
                        .background(Theme.border(dark).opacity(0.6), in: RoundedRectangle(cornerRadius: 12))
                }.buttonStyle(.plain)
            }
            .padding(.bottom, 8)
            Divider()
            ForEach([AppScreen.home, .jobs, .punch, .photos, .money]) { row($0) }
            Divider().padding(.vertical, 4)
            Button { textSize = (textSize + 1) % 3 } label: {
                tool(icon: nil, aa: true, title: "Text size", sub: sizeNames[min(max(textSize, 0), 2)])
            }.buttonStyle(.plain)
            Button { dark.toggle() } label: {
                tool(icon: "circle.lefthalf.filled", aa: false, title: "Light / Dark", sub: dark ? "Dark" : "Light")
            }.buttonStyle(.plain)
            row(.search)
            row(.calendar)
            Spacer()
        }
        .padding(12)
        .frame(width: 300)
        .frame(maxHeight: .infinity)
        .background(Theme.card(dark).ignoresSafeArea())
        .overlay(alignment: .trailing) { Rectangle().fill(Theme.border(dark)).frame(width: 1).ignoresSafeArea() }
    }

    private func row(_ s: AppScreen) -> some View {
        let on = screen == s
        return Button {
            screen = s
            withAnimation(.easeOut(duration: 0.25)) { menu = false }
        } label: {
            HStack(spacing: 16) {
                Image(systemName: s.symbol).font(.title3).frame(width: 28)
                Text(s.rawValue).font(.title3.weight(.heavy))
                Spacer()
            }
            .padding(.horizontal, 16).frame(minHeight: 56)
            .foregroundStyle(on ? Theme.blue : Color.primary)
            .background(on ? Theme.blue.opacity(0.16) : .clear, in: RoundedRectangle(cornerRadius: 14))
        }.buttonStyle(.plain)
    }

    private func tool(icon: String?, aa: Bool, title: String, sub: String) -> some View {
        HStack(spacing: 16) {
            if aa { Text("Aa").font(.title3.weight(.black)).frame(width: 28) }
            else if let icon { Image(systemName: icon).font(.title3).frame(width: 28) }
            VStack(alignment: .leading, spacing: 1) {
                Text(title).font(.headline.weight(.heavy))
                Text(sub).font(.footnote.weight(.bold)).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.horizontal, 16).frame(minHeight: 52).contentShape(Rectangle())
    }
}

// MARK: - Home (matches the web field app's Home screen)

struct HomeView: View {
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @Query private var photos: [SitePhoto]
    @AppStorage("bpDark") private var dark = true
    @AppStorage("bpActiveJob") private var activeKey = ""
    @StateObject private var info = HeaderInfo()
    let go: (AppScreen) -> Void
    @State private var path: [Route] = []

    struct Route: Hashable { let job: Job; let tab: JobTab }

    private var greeting: String {
        let h = Calendar.current.component(.hour, from: Date())
        return h < 12 ? "Good Morning" : (h < 17 ? "Good Afternoon" : "Good Evening")
    }
    private func key(_ j: Job) -> String { String(j.created.timeIntervalSince1970) }
    private var active: Job? { jobs.first { key($0) == activeKey } ?? jobs.first { $0.isActive } ?? jobs.first }
    private var version: String { "v" + ((Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "") }

    var body: some View {
        NavigationStack(path: $path) {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    top
                    if let job = active {
                        picker(job)
                        Divider().padding(.horizontal, -16)
                        siteCard(job)
                        quickTiles(job)
                        attention(job)
                    } else {
                        Text("No jobs yet. Open the menu → Jobs to add one or import your backup.")
                            .foregroundStyle(.secondary).padding(.top, 8)
                    }
                }
                .padding(16)
            }
            .background(Theme.bg(dark))
            .navigationDestination(for: Route.self) { JobDetailView(job: $0.job, start: $0.tab) }
            .toolbar { ToolbarItem(placement: .navigation) { MenuButton() } }
            .navigationTitle("")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .onAppear { info.start() }
        }
    }

    // MARK: header

    private var top: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .center, spacing: 12) {
                VStack(spacing: 2) {
                    ZStack {
                        Circle().stroke(Color.primary, lineWidth: 3).frame(width: 58, height: 58)
                        Text("B").font(.system(size: 32, weight: .bold, design: .serif))
                        Capsule().fill(Color.red).frame(width: 22, height: 3).offset(y: 14)
                    }
                    Text(version).font(.caption.weight(.bold)).foregroundStyle(.secondary)
                }
                Text(greeting)
                    .font(.system(size: 40, weight: .regular))
                    .minimumScaleFactor(0.5).lineLimit(1)
                    .foregroundStyle(LinearGradient(colors: [Theme.blue, Theme.orange], startPoint: .leading, endPoint: .trailing))
            }
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "mappin.and.ellipse").font(.title3).foregroundStyle(Theme.blue).padding(.top, 2)
                Text(info.place).font(.headline).fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 6)
                TimelineView(.everyMinute) { ctx in
                    Text(ctx.date.formatted(.dateTime.hour().minute()))
                        .font(.system(size: 36, weight: .regular)).foregroundStyle(Theme.blue)
                        .minimumScaleFactor(0.6).lineLimit(1)
                }
            }
            Text(Date.now.formatted(.dateTime.weekday(.abbreviated).month(.twoDigits).day(.twoDigits).year()))
                .font(.title3).foregroundStyle(.secondary).padding(.leading, 30)
            HStack(spacing: 10) {
                Text(info.icon).font(.title2)
                Text(info.weather).font(.title3.weight(.semibold)).foregroundStyle(.secondary).lineLimit(1).minimumScaleFactor(0.7)
            }
        }
    }

    private func picker(_ job: Job) -> some View {
        Menu {
            ForEach(jobs) { j in Button(j.name) { activeKey = key(j) } }
        } label: {
            HStack(spacing: 12) {
                Image(systemName: "mappin.and.ellipse").font(.title3).foregroundStyle(Theme.blue)
                Text("ON SITE").font(.subheadline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                Text(job.name).font(.title3.weight(.bold)).foregroundStyle(Theme.blue).lineLimit(1)
                Spacer()
                Image(systemName: "chevron.up.chevron.down").foregroundStyle(.secondary)
            }
            .padding(.horizontal, 16).frame(minHeight: 60)
            .background(Theme.blue.opacity(0.10), in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.blue.opacity(0.55), lineWidth: 1.5))
        }.buttonStyle(.plain)
    }

    // MARK: active job card

    private func siteCard(_ job: Job) -> some View {
        let open = job.totalCount - job.doneCount
        let today = (job.photos ?? []).filter { Calendar.current.isDateInToday($0.created) }.count
        let next = (job.appointments ?? []).filter { $0.date >= Date() }.sorted { $0.date < $1.date }.first
        return VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("ON SITE NOW").font(.headline.weight(.heavy)).tracking(1.5).foregroundStyle(Theme.blue)
                Spacer()
                Button { path.append(Route(job: job, tab: .spaces)) } label: {
                    Text("Open job ›").font(.headline.weight(.bold)).foregroundStyle(Theme.blue)
                }.buttonStyle(.plain)
            }
            Text(job.name).font(.system(size: 32, weight: .heavy)).lineLimit(2).minimumScaleFactor(0.7)
            if !job.client.isEmpty { Text(job.client).font(.title3).foregroundStyle(.secondary) }
            if !job.address.isEmpty {
                HStack(spacing: 8) {
                    Image(systemName: "mappin.and.ellipse").foregroundStyle(Theme.blue)
                    Text(job.address).font(.callout.weight(.semibold))
                }
            }
            HStack {
                Text("Progress").font(.title3).foregroundStyle(.secondary)
                Spacer()
                Text("\(job.percent)%").font(.title3.weight(.bold)).foregroundStyle(Theme.blue)
            }
            ProgressView(value: Double(job.percent), total: 100).tint(Theme.blue).scaleEffect(x: 1, y: 2.4, anchor: .center)
            HStack(spacing: 10) {
                stat("\(open)", "OPEN PUNCH", Theme.orange) { path.append(Route(job: job, tab: .punch)) }
                stat("\(today)", "PHOTOS TODAY", Theme.blue) { path.append(Route(job: job, tab: .photos)) }
                stat((job.remaining < 0 ? "−" : "") + Money.text(abs(job.remaining)).replacingOccurrences(of: ".00", with: ""),
                     "MONEY LEFT", job.remaining < 0 ? .red : .green) { path.append(Route(job: job, tab: .money)) }
            }
            HStack(spacing: 10) {
                Text("NEXT").font(.subheadline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                Text(next.map { "\($0.title.isEmpty ? "Appointment" : $0.title) · " + $0.date.formatted(date: .abbreviated, time: .shortened) } ?? "Nothing scheduled")
                    .font(.title3.weight(.semibold)).lineLimit(1).minimumScaleFactor(0.7)
            }
        }
        .padding(18)
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 26))
        .overlay(RoundedRectangle(cornerRadius: 26).stroke(Theme.blue.opacity(0.55), lineWidth: 1.5))
    }

    private func stat(_ value: String, _ label: String, _ color: Color, _ tap: @escaping () -> Void) -> some View {
        Button(action: tap) {
            VStack(spacing: 6) {
                Text(value).font(.system(size: 30, weight: .heavy)).foregroundStyle(color).minimumScaleFactor(0.5).lineLimit(1)
                Text(label).font(.subheadline.weight(.heavy)).tracking(1).foregroundStyle(.secondary)
                    .multilineTextAlignment(.center).minimumScaleFactor(0.7)
            }
            .frame(maxWidth: .infinity, minHeight: 112)
            .background(Color.primary.opacity(0.06), in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border(dark)))
        }.buttonStyle(.plain)
    }

    // MARK: quick tiles + attention

    private func quickTiles(_ job: Job) -> some View {
        HStack(spacing: 12) {
            tile("cart", Theme.orange) { path.append(Route(job: job, tab: .shopping)) }
            tile("list.clipboard", Theme.blue) { path.append(Route(job: job, tab: .notes)) }
            tile("doc.text", .green) { path.append(Route(job: job, tab: .reports)) }
        }
    }

    private func tile(_ symbol: String, _ color: Color, _ tap: @escaping () -> Void) -> some View {
        Button(action: tap) {
            Image(systemName: symbol).font(.system(size: 34)).foregroundStyle(color)
                .frame(maxWidth: .infinity, minHeight: 92)
                .background(color.opacity(0.14), in: RoundedRectangle(cornerRadius: 22))
                .overlay(RoundedRectangle(cornerRadius: 22).stroke(color.opacity(0.7), lineWidth: 1.5))
        }.buttonStyle(.plain)
    }

    private struct Flag: Identifiable { let id = UUID(); let text: String; let symbol: String; let color: Color; let tab: JobTab }

    private func flags(_ job: Job) -> [Flag] {
        var out: [Flag] = []
        let urgent = (job.punchItems ?? []).filter { !$0.done && ($0.priority == "High" || $0.priority == "Critical") }.count
        if urgent > 0 { out.append(Flag(text: "\(urgent) high-priority punch item\(urgent == 1 ? "" : "s") open", symbol: "exclamationmark.triangle.fill", color: Theme.orange, tab: .punch)) }
        let late = (job.invoices ?? []).filter { $0.status == "Overdue" }.count
        if late > 0 { out.append(Flag(text: "\(late) overdue invoice\(late == 1 ? "" : "s")", symbol: "dollarsign.circle.fill", color: .red, tab: .money)) }
        let cos = (job.changeOrders ?? []).filter { $0.status == "Submitted" }.count
        if cos > 0 { out.append(Flag(text: "\(cos) change order\(cos == 1 ? "" : "s") waiting for approval", symbol: "doc.badge.clock.fill", color: Theme.blue, tab: .money)) }
        let soon = Calendar.current.date(byAdding: .day, value: 30, to: Date()) ?? Date()
        let permits = (job.permits ?? []).filter { $0.status == "Active" && $0.expirationDate < soon }.count
        if permits > 0 { out.append(Flag(text: "\(permits) permit\(permits == 1 ? "" : "s") expiring within 30 days", symbol: "clock.badge.exclamationmark.fill", color: Theme.orange, tab: .money)) }
        return out
    }

    private func attention(_ job: Job) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("NEEDS YOUR ATTENTION").font(.headline.weight(.heavy)).tracking(2).foregroundStyle(.secondary).padding(.top, 6)
            let list = flags(job)
            if list.isEmpty {
                Label("All clear on this job", systemImage: "checkmark.seal.fill").foregroundStyle(.green).font(.title3.weight(.semibold))
            }
            ForEach(list) { f in
                Button { path.append(Route(job: job, tab: f.tab)) } label: {
                    HStack(spacing: 12) {
                        Image(systemName: f.symbol).foregroundStyle(f.color).font(.title3)
                        Text(f.text).font(.headline).multilineTextAlignment(.leading)
                        Spacer()
                        Image(systemName: "chevron.right").foregroundStyle(.secondary)
                    }
                    .padding(14)
                    .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
                    .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark)))
                }.buttonStyle(.plain)
            }
        }
    }
}

struct JobCard: View {
    let job: Job
    @AppStorage("bpDark") private var dark = true
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(job.name).font(.headline).lineLimit(1)
            if !job.address.isEmpty { Text(job.address).font(.subheadline).foregroundStyle(.secondary).lineLimit(1) }
            HStack {
                ProgressView(value: Double(job.percent), total: 100).tint(Theme.blue)
                Text("\(job.percent)%").font(.callout.bold())
            }
            Text("\(job.doneCount)/\(job.totalCount) done").font(.callout).foregroundStyle(.secondary)
        }
        .padding(14).frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark)))
    }
}

// MARK: - Punch (open items across all jobs)

struct AllPunchView: View {
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    private var open: Int { jobs.reduce(0) { $0 + ($1.totalCount - $1.doneCount) } }

    var body: some View {
        NavigationStack {
            List {
                ForEach(jobs.filter { $0.totalCount > $0.doneCount }) { job in
                    Section(job.name) {
                        ForEach((job.punchItems ?? []).filter { !$0.done }.sorted { $0.created > $1.created }) { item in
                            NavigationLink { PunchDetail(item: item) } label: {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(item.text).font(.headline).lineLimit(2)
                                    Text(item.space?.name ?? "General").font(.subheadline).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden).background(Theme.bg(dark))
            .overlay { if open == 0 { ContentUnavailableView("Nothing open", systemImage: "checkmark.circle", description: Text("Every punch item is done.")) } }
            .navigationTitle("Punch")
            .toolbar { ToolbarItem(placement: .navigation) { MenuButton() } }
        }
    }
}

// MARK: - Photos (recent across all jobs)

struct AllPhotosView: View {
    @Query(sort: \SitePhoto.created, order: .reverse) private var photos: [SitePhoto]
    @AppStorage("bpDark") private var dark = true
    private let cols = [GridItem(.adaptive(minimum: 110), spacing: 4)]

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVGrid(columns: cols, spacing: 4) {
                    ForEach(photos.prefix(300)) { p in
                        NavigationLink { if let j = p.job { JobDetailView(job: j) } } label: { PhotoThumb(photo: p) }
                            .buttonStyle(.plain)
                    }
                }.padding(4)
            }
            .background(Theme.bg(dark))
            .overlay { if photos.isEmpty { ContentUnavailableView("No photos yet", systemImage: "camera") } }
            .navigationTitle("Photos")
            .toolbar { ToolbarItem(placement: .navigation) { MenuButton() } }
            .navigationSubtitleCompat("\(photos.count) photos")
        }
    }
}

private extension View {
    @ViewBuilder func navigationSubtitleCompat(_ s: String) -> some View {
        #if os(macOS)
        self.navigationSubtitle(s)
        #else
        self
        #endif
    }
}

// MARK: - Money (every job at a glance)

struct AllMoneyView: View {
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true

    private func usd(_ v: Double) -> String { v.formatted(.currency(code: "USD").precision(.fractionLength(0))) }

    var body: some View {
        NavigationStack {
            List {
                Section("All jobs") {
                    line("Contracts", usd(jobs.reduce(0) { $0 + $1.revisedContract }))
                    line("Invoiced", usd(jobs.reduce(0) { $0 + $1.invoiced }))
                    line("Collected", usd(jobs.reduce(0) { $0 + $1.collected }), Theme.blue)
                    line("Outstanding", usd(jobs.reduce(0) { $0 + $1.outstanding }), Theme.orange)
                    line("Costs", usd(jobs.reduce(0) { $0 + $1.totalCost }))
                }
                Section("By job") {
                    ForEach(jobs) { job in
                        NavigationLink { JobDetailView(job: job) } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(job.name).font(.headline).lineLimit(1)
                                HStack {
                                    Text("Contract \(usd(job.revisedContract))")
                                    Spacer()
                                    Text("Margin \(job.marginPercent)%").foregroundStyle(job.remaining >= 0 ? .green : .red)
                                }.font(.subheadline).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden).background(Theme.bg(dark))
            .navigationTitle("Money")
            .toolbar { ToolbarItem(placement: .navigation) { MenuButton() } }
        }
    }

    private func line(_ a: String, _ b: String, _ c: Color = .primary) -> some View {
        HStack { Text(a); Spacer(); Text(b).bold().foregroundStyle(c) }
    }
}

// MARK: - Search (jobs, punch items, notes)

struct SearchView: View {
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @State private var q = ""

    private var term: String { q.trimmingCharacters(in: .whitespaces).lowercased() }
    private var jobHits: [Job] { jobs.filter { $0.name.lowercased().contains(term) || $0.client.lowercased().contains(term) || $0.address.lowercased().contains(term) } }
    private var punchHits: [PunchItem] { jobs.flatMap { $0.punchItems ?? [] }.filter { $0.text.lowercased().contains(term) } }
    private var noteHits: [JobNote] { jobs.flatMap { $0.notes ?? [] }.filter { $0.title.lowercased().contains(term) || $0.text.lowercased().contains(term) } }

    var body: some View {
        NavigationStack {
            List {
                if !term.isEmpty {
                    if !jobHits.isEmpty { Section("Jobs") { ForEach(jobHits) { j in NavigationLink(j.name) { JobDetailView(job: j) } } } }
                    if !punchHits.isEmpty { Section("Punch items") { ForEach(punchHits.prefix(50)) { p in NavigationLink { PunchDetail(item: p) } label: { VStack(alignment: .leading) { Text(p.text); Text(p.job?.name ?? "").font(.subheadline).foregroundStyle(.secondary) } } } } }
                    if !noteHits.isEmpty { Section("Notes") { ForEach(noteHits.prefix(50)) { n in NavigationLink { if let j = n.job { JobDetailView(job: j) } } label: { Text(n.title.isEmpty ? n.text : n.title).lineLimit(2) } } } }
                }
            }
            .scrollContentBackground(.hidden).background(Theme.bg(dark))
            .searchable(text: $q, prompt: "Search jobs, punch items, notes")
            .overlay { if term.isEmpty { ContentUnavailableView("Search", systemImage: "magnifyingglass", description: Text("Type to search every job.")) }
                       else if jobHits.isEmpty && punchHits.isEmpty && noteHits.isEmpty { ContentUnavailableView.search(text: q) } }
            .navigationTitle("Search")
            .toolbar { ToolbarItem(placement: .navigation) { MenuButton() } }
        }
    }
}

// MARK: - Calendar (every job's appointments, month grid like the web app)

struct AllCalendarView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Appointment.date) private var all: [Appointment]
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @State private var month = Calendar.current.date(from: Calendar.current.dateComponents([.year, .month], from: Date())) ?? Date()
    @State private var picked: Date? = Calendar.current.startOfDay(for: Date())

    private var cal: Calendar { Calendar.current }
    private func count(on day: Date) -> Int { all.filter { cal.isDate($0.date, inSameDayAs: day) }.count }

    private var cells: [Date?] {
        guard let range = cal.range(of: .day, in: .month, for: month) else { return [] }
        let blanks = (cal.component(.weekday, from: month) - cal.firstWeekday + 7) % 7
        var out: [Date?] = Array(repeating: nil, count: blanks)
        for d in range { out.append(cal.date(byAdding: .day, value: d - 1, to: month)) }
        return out
    }
    private var shown: [Appointment] {
        guard let d = picked else { return all.filter { $0.date >= cal.startOfDay(for: Date()) } }
        return all.filter { cal.isDate($0.date, inSameDayAs: d) }
    }

    var body: some View {
        NavigationStack {
            List {
                Section { header; grid }
                Section(picked.map { $0.formatted(date: .complete, time: .omitted) } ?? "Upcoming") {
                    if shown.isEmpty { Text(picked == nil ? "Nothing upcoming." : "Nothing this day. Tap the day again to see upcoming.").foregroundStyle(.secondary) }
                    ForEach(shown) { a in
                        NavigationLink { AppointmentDetail(item: a) } label: {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(a.title.isEmpty ? "Appointment" : a.title).font(.headline).lineLimit(1)
                                Text(a.date.formatted(date: picked == nil ? .abbreviated : .omitted, time: .shortened) + " · " + a.kind + (a.job.map { " · " + $0.name } ?? ""))
                                    .font(.callout).foregroundStyle(.secondary)
                            }
                        }
                    }
                    .onDelete { idx in idx.forEach { context.delete(shown[$0]) } }
                }
            }
            .scrollContentBackground(.hidden).background(Theme.bg(dark))
            .navigationTitle("Calendar")
            .toolbar {
                ToolbarItem(placement: .navigation) { MenuButton() }
                ToolbarItem(placement: .primaryAction) {
                    Menu {
                        ForEach(jobs) { j in Button(j.name) { add(to: j) } }
                    } label: { Image(systemName: "plus") }
                }
            }
        }
    }

    private var header: some View {
        HStack {
            Button { shift(-1) } label: { Image(systemName: "chevron.left") }.buttonStyle(.plain)
            Spacer()
            Text(month.formatted(.dateTime.month(.wide).year())).font(.title3.bold())
            Spacer()
            Button { shift(1) } label: { Image(systemName: "chevron.right") }.buttonStyle(.plain)
        }
    }

    private var grid: some View {
        let cols = Array(repeating: GridItem(.flexible(), spacing: 4), count: 7)
        return LazyVGrid(columns: cols, spacing: 4) {
            ForEach(Array(cal.veryShortWeekdaySymbols.enumerated()), id: \.offset) { _, d in
                Text(d).font(.callout).foregroundStyle(.secondary)
            }
            ForEach(Array(cells.enumerated()), id: \.offset) { _, day in
                if let day { dayCell(day) } else { Color.clear.frame(height: 44) }
            }
        }
    }

    private func dayCell(_ day: Date) -> some View {
        let n = count(on: day)
        let isPicked = picked.map { cal.isDate($0, inSameDayAs: day) } ?? false
        return Button { picked = isPicked ? nil : cal.startOfDay(for: day) } label: {
            VStack(spacing: 2) {
                Text("\(cal.component(.day, from: day))").font(.body.weight(cal.isDateInToday(day) ? .bold : .regular))
                Circle().fill(n > 0 ? Theme.orange : Color.clear).frame(width: 7, height: 7)
            }
            .frame(maxWidth: .infinity, minHeight: 44)
            .background(isPicked ? Theme.blue.opacity(0.35) : (cal.isDateInToday(day) ? Color.gray.opacity(0.2) : Color.clear),
                        in: RoundedRectangle(cornerRadius: 8))
        }.buttonStyle(.plain)
    }

    private func shift(_ by: Int) { if let m = cal.date(byAdding: .month, value: by, to: month) { month = m } }

    private func add(to job: Job) {
        let a = Appointment(title: "New appointment")
        let base = picked ?? cal.startOfDay(for: Date())
        a.date = cal.date(bySettingHour: 9, minute: 0, second: 0, of: base) ?? base
        a.job = job
        context.insert(a)
    }
}
