import SwiftUI
import PhotosUI
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
    @State private var syncNote = false
    @State private var feedbackNote = false
    @StateObject private var shell = ShellState()

    private var dynamicSize: DynamicTypeSize { [DynamicTypeSize.large, .xLarge, .xxxLarge][min(max(textSize, 0), 2)] }
    private let sizeNames = ["Normal", "Large", "Extra large"]

    private var zoom: CGFloat { [1.0, 1.15, 1.32][min(max(textSize, 0), 2)] }

    var body: some View {
        #if os(macOS)
        // macOS ignores Dynamic Type, so Text size zooms the whole layout instead.
        GeometryReader { g in
            content
                .frame(width: g.size.width / zoom, height: g.size.height / zoom)
                .scaleEffect(zoom, anchor: .topLeading)
                .frame(width: g.size.width, height: g.size.height, alignment: .topLeading)
        }
        #else
        content
        #endif
    }

    private var content: some View {
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
            .environmentObject(shell)
            .overlay(alignment: .bottomTrailing) {
                FloatBar(showBack: screen != .home)
                    .environment(\.openMenu, { withAnimation(.easeOut(duration: 0.25)) { menu = true } })
                    .environmentObject(shell)
            }
            .onAppear { shell.goHome = { screen = .home }; installScrollWatch() }
            .onChange(of: screen) { _, _ in shell.barHidden = false }
            .simultaneousGesture(DragGesture(minimumDistance: 14).onChanged { v in
                // finger moving up = scrolling down: hide; finger moving down: show
                if v.translation.height < -24 { if !shell.barHidden { shell.barHidden = true } }
                else if v.translation.height > 24 { if shell.barHidden { shell.barHidden = false } }
            })

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
        .alert("Sync", isPresented: $syncNote) { Button("OK", role: .cancel) {} } message: { Text("Your jobs sync through iCloud automatically on every device signed in to your Apple ID.") }
        .alert("Send feedback", isPresented: $feedbackNote) { Button("OK", role: .cancel) {} } message: { Text("The feedback form is not set up yet.") }
    }

    #if os(macOS)
    @State private var scrollMonitor: Any?
    private func installScrollWatch() {
        guard scrollMonitor == nil else { return }
        scrollMonitor = NSEvent.addLocalMonitorForEvents(matching: .scrollWheel) { e in
            // natural scrolling: negative deltaY = content moving up = scrolling down the page
            if e.scrollingDeltaY < -2 { shell.barHidden = true } else if e.scrollingDeltaY > 2 { shell.barHidden = false }
            return e
        }
    }
    #else
    private func installScrollWatch() {}
    #endif

    private var drawer: some View {
        VStack(alignment: .leading, spacing: 8) {
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
            Button { syncNote = true } label: { tool(icon: "arrow.triangle.2.circlepath", aa: false, title: "Sync", sub: "iCloud · automatic") }.buttonStyle(.plain)
            Button { feedbackNote = true } label: { tool(icon: "bubble.left", aa: false, title: "Send feedback", sub: "") }.buttonStyle(.plain)
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
            HStack(spacing: 18) {
                Image(systemName: s.symbol).font(.title2).frame(width: 36)
                Text(s.rawValue).font(.title3.weight(.heavy))
                Spacer()
            }
            .padding(.horizontal, 12).frame(minHeight: 64)
            .foregroundStyle(on ? Theme.blue : Color.primary)
            .background(on ? Theme.blue.opacity(0.16) : .clear, in: RoundedRectangle(cornerRadius: 14))
        }.buttonStyle(.plain)
    }

    private func tool(icon: String?, aa: Bool, title: String, sub: String) -> some View {
        HStack(spacing: 18) {
            if aa { Text("Aa").font(.title2.weight(.black)).frame(width: 36) }
            else if let icon { Image(systemName: icon).font(.title2).frame(width: 36) }
            VStack(alignment: .leading, spacing: 1) {
                Text(title).font(.headline.weight(.heavy))
                Text(sub).font(.footnote.weight(.bold)).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.horizontal, 12).frame(minHeight: 64).contentShape(Rectangle())
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
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
            .onAppear { info.start() }
        }
    }

    // MARK: header

    private var top: some View {
        VStack(alignment: .leading, spacing: 4) {
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
            HStack(alignment: .center, spacing: 10) {
                VStack(alignment: .leading, spacing: 3) {
                    HStack(alignment: .top, spacing: 10) {
                        FeatherPin().stroke(Theme.blue, style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
                            .frame(width: 20, height: 20).padding(.top, 2)
                        VStack(alignment: .leading, spacing: 1) {
                            Text(info.place).font(.headline.weight(.bold)).fixedSize(horizontal: false, vertical: true)
                            Text(Date.now.formatted(.dateTime.weekday(.abbreviated).month(.twoDigits).day(.twoDigits).year()))
                                .font(.callout.weight(.semibold)).foregroundStyle(.secondary)
                        }
                    }
                    HStack(spacing: 10) {
                        Image(systemName: info.icon).font(.title3).foregroundStyle(Color.primary).frame(width: 20)
                        Text(info.weather).font(.callout.weight(.bold)).foregroundStyle(.secondary).lineLimit(1).minimumScaleFactor(0.7)
                    }
                }
                Spacer(minLength: 6)
                TimelineView(.everyMinute) { ctx in
                    Text(ctx.date.formatted(.dateTime.hour().minute()))
                        .font(.system(size: 36, weight: .regular)).foregroundStyle(Theme.blue)
                        .minimumScaleFactor(0.6).lineLimit(1)
                }
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
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @AppStorage("bpActiveJob") private var activeKey = ""
    @State private var status = "Open"            // Open, Done, All
    @State private var spaceName = "All"           // All, General, or a space name
    @State private var trade = ""                  // "" = any
    @State private var addSheet = false
    @State private var newText = ""
    @State private var toDelete: PunchItem?

    private func key(_ j: Job) -> String { String(j.created.timeIntervalSince1970) }
    private var job: Job? { jobs.first { key($0) == activeKey } ?? jobs.first }
    private var items: [PunchItem] { job?.punchItems ?? [] }
    private var openCount: Int { items.filter { !$0.done }.count }
    private var doneCount: Int { items.filter { $0.done }.count }
    private var filterCount: Int { (status != "All" ? 1 : 0) + (spaceName != "All" ? 1 : 0) + (trade.isEmpty ? 0 : 1) }

    private var shown: [PunchItem] {
        items.filter { i in
            (status == "All" || (status == "Open" ? !i.done : i.done)) &&
            (spaceName == "All" || (spaceName == "General" ? i.space == nil : i.space?.name == spaceName)) &&
            (trade.isEmpty || i.trade == trade)
        }
    }
    private struct Group: Identifiable { let id: String; let space: Space?; let items: [PunchItem] }
    private var groups: [Group] {
        var out: [Group] = []
        let general = shown.filter { $0.space == nil }
        if !general.isEmpty { out.append(Group(id: "general", space: nil, items: general.sorted { $0.created < $1.created })) }
        let spaces = (job?.spaces ?? []).sorted { ($0.level, $0.order) < ($1.level, $1.order) }
        for sp in spaces {
            let list = shown.filter { $0.space?.uid == sp.uid }
            if !list.isEmpty { out.append(Group(id: sp.uid.uuidString, space: sp, items: list.sorted { $0.created < $1.created })) }
        }
        return out
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    TopBar(title: "Punch", sub: "\(openCount) open · \(doneCount) done")
                    if let job {
                        HStack(spacing: 12) {
                            Menu {
                                ForEach(jobs) { j in Button(j.name) { activeKey = key(j); spaceName = "All" } }
                            } label: {
                                HStack { Text(job.name).font(.title3.weight(.semibold)); Spacer(); Image(systemName: "chevron.down").font(.footnote.weight(.bold)) }
                                    .foregroundStyle(.primary).padding(.horizontal, 18).frame(height: 56)
                                    .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
                                    .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark), lineWidth: 1))
                            }
                            .menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                            NavigationLink { JobDetailView(job: job) } label: {
                                Label("Areas", systemImage: "square.grid.2x2").font(.title3.weight(.bold)).foregroundStyle(Theme.blue)
                                    .padding(.horizontal, 18).frame(height: 56)
                                    .background(Theme.blue.opacity(0.12), in: RoundedRectangle(cornerRadius: 16))
                                    .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.blue.opacity(0.5), lineWidth: 1))
                            }.buttonStyle(.plain)
                        }
                        NavigationLink { PunchListView(job: job, space: nil) } label: {
                            let g = items.filter { $0.space == nil }
                            Text("General \(g.filter { $0.done }.count)/\(g.count)").font(.headline.weight(.semibold)).foregroundStyle(Theme.red)
                                .padding(.horizontal, 20).frame(height: 46)
                                .overlay(Capsule().stroke(Theme.border(dark), lineWidth: 1))
                        }.buttonStyle(.plain)
                        HStack(spacing: 12) {
                            filterMenu("Status", status) {
                                ForEach(["Open", "Done", "All"], id: \.self) { v in Button(v) { status = v } }
                            }
                            filterMenu("Space", spaceName) {
                                Button("All") { spaceName = "All" }
                                Button("General") { spaceName = "General" }
                                ForEach(job.spaces ?? []) { sp in Button(sp.name) { spaceName = sp.name } }
                            }
                        }
                        Menu {
                            Button("Any trade") { trade = "" }
                            ForEach(Trades.all, id: \.self) { t in Button(t) { trade = t } }
                            Divider()
                            Button("Reset filters") { status = "Open"; spaceName = "All"; trade = "" }
                        } label: {
                            Label("Filter (\(filterCount)) ▾", systemImage: "line.3.horizontal.decrease").font(.title3.weight(.bold))
                                .foregroundStyle(Theme.blue).frame(maxWidth: .infinity).frame(height: 54)
                                .background(Theme.blue.opacity(0.12), in: RoundedRectangle(cornerRadius: 16))
                                .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.blue.opacity(0.6), lineWidth: 1))
                        }
                        .menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                        Text("Showing \(shown.count) of \(items.count)").font(.headline.weight(.semibold)).foregroundStyle(Theme.blue)
                        ForEach(groups) { g in group(g, job) }
                        if shown.isEmpty { Text("Nothing matches these filters.").foregroundStyle(.secondary).padding(.top, 20) }
                    } else {
                        Text("Add a job first.").foregroundStyle(.secondary)
                    }
                    Color.clear.frame(height: 110)
                }
                .padding(.horizontal, 16).padding(.top, 8)
            }
            .background(Theme.bg(dark))
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
            .shellAdd { addSheet = true }
            .alert("Add punch item", isPresented: $addSheet) {
                TextField("What needs doing", text: $newText)
                Button("Add") {
                    let t = newText.trimmingCharacters(in: .whitespaces)
                    if let job, !t.isEmpty {
                        let it = PunchItem(text: t, trade: ""); it.job = job
                        if spaceName != "All" && spaceName != "General" { it.space = (job.spaces ?? []).first { $0.name == spaceName } }
                        context.insert(it)
                    }
                    newText = ""
                }
                Button("Cancel", role: .cancel) { newText = "" }
            }
            .confirmationDialog("Delete this punch item?", isPresented: Binding(get: { toDelete != nil }, set: { if !$0 { toDelete = nil } }), titleVisibility: .visible) {
                Button("Delete", role: .destructive) { if let t = toDelete { context.delete(t) }; toDelete = nil }
                Button("Cancel", role: .cancel) { toDelete = nil }
            }
        }
    }

    private func filterMenu<C: View>(_ title: String, _ value: String, @ViewBuilder _ content: () -> C) -> some View {
        Menu { content() } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.headline.weight(.semibold)).foregroundStyle(.secondary)
                    Text(value).font(.title3.weight(.bold)).foregroundStyle(.primary).lineLimit(1)
                }
                Spacer()
                Image(systemName: "line.3.horizontal").font(.title3.weight(.bold)).foregroundStyle(.primary)
            }
            .padding(.horizontal, 16).frame(height: 64)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark), lineWidth: 1))
        }
        .menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
    }

    private func group(_ g: Group, _ job: Job) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                NavigationLink { PunchListView(job: job, space: g.space) } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "door.left.hand.closed")
                        Text(g.space?.name ?? "General")
                        Image(systemName: "chevron.right").font(.footnote.weight(.bold))
                    }.font(.title3.weight(.bold)).foregroundStyle(Theme.blue)
                }.buttonStyle(.plain)
                Spacer()
                let all = items.filter { $0.space?.uid == g.space?.uid }
                Text("\(all.filter { $0.done }.count)/\(all.count)").font(.headline.weight(.bold)).foregroundStyle(Theme.red)
            }.padding(.top, 8)
            ForEach(g.items) { it in card(it) }
        }
    }

    private func card(_ it: PunchItem) -> some View {
        HStack(spacing: 14) {
            Button { it.done.toggle(); it.completed = it.done ? Date() : nil } label: {
                RoundedRectangle(cornerRadius: 12).stroke(it.done ? Theme.green : Theme.red, lineWidth: 3)
                    .frame(width: 38, height: 38)
                    .overlay { if it.done { Image(systemName: "checkmark").font(.headline.weight(.bold)).foregroundStyle(Theme.green) } }
            }.buttonStyle(.plain)
            NavigationLink { PunchDetail(item: it) } label: {
                VStack(alignment: .leading, spacing: 2) {
                    Text(it.text.isEmpty ? "Punch item" : it.text).font(.title3.weight(.semibold)).foregroundStyle(.primary)
                        .strikethrough(it.done).multilineTextAlignment(.leading)
                    Text("Added " + it.created.formatted(.dateTime.month(.twoDigits).day(.twoDigits))).font(.headline).foregroundStyle(.secondary)
                    Text("· " + (it.done ? "done" : "open")).font(.headline.weight(.bold)).foregroundStyle(it.done ? Theme.green : Theme.red)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }.buttonStyle(.plain)
            NavigationLink { PunchDetail(item: it) } label: {
                let n = (it.photos ?? []).count
                ZStack(alignment: .topTrailing) {
                    RoundedRectangle(cornerRadius: 14).stroke(Color.secondary.opacity(0.5), style: StrokeStyle(lineWidth: 1.5, dash: [5, 4]))
                        .frame(width: 56, height: 56)
                        .overlay(Image(systemName: "camera").font(.title3).foregroundStyle(.secondary))
                    if n > 0 { Text("\(n)").font(.caption2.weight(.bold)).foregroundStyle(.white).padding(4).background(Theme.blue, in: Circle()).offset(x: 6, y: -6) }
                }
            }.buttonStyle(.plain)
            Button { toDelete = it } label: { Image(systemName: "xmark").font(.headline).foregroundStyle(.secondary).frame(width: 30, height: 40) }.buttonStyle(.plain)
        }
        .padding(.vertical, 14).padding(.leading, 18).padding(.trailing, 10)
        .background((it.done ? Theme.green : Theme.red).opacity(0.07), in: RoundedRectangle(cornerRadius: 18))
        .overlay(alignment: .leading) {
            UnevenRoundedRectangle(topLeadingRadius: 18, bottomLeadingRadius: 18).fill(it.done ? Theme.green : Theme.red).frame(width: 5)
        }
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border(dark), lineWidth: 1))
    }
}

// MARK: - Photos (recent across all jobs)

struct AllPhotosView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @Query(sort: \SitePhoto.created, order: .reverse) private var photos: [SitePhoto]
    @AppStorage("bpDark") private var dark = true
    @AppStorage("bpStamp") private var stamp = true
    @State private var pick = ""                       // "" = All Jobs
    @State private var picking = false
    @State private var picked: [PhotosPickerItem] = []

    private func key(_ j: Job) -> String { String(j.created.timeIntervalSince1970) }
    private var shownJobs: [Job] { pick.isEmpty ? jobs : jobs.filter { key($0) == pick } }
    private var target: Job? { shownJobs.first }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    TopBar(title: "Photos", sub: "\(photos.count) photos · \(photos.filter { $0.space == nil }.count) unfiled")
                    HStack(spacing: 12) {
                        NavigationLink { PhotoTimeline(photos: photos) } label: {
                            HStack(spacing: 10) {
                                Image(systemName: "camera")
                                Text("BuildersCam Timeline").multilineTextAlignment(.center)
                            }.font(.title3.weight(.bold)).foregroundStyle(.white)
                            .frame(maxWidth: .infinity).frame(height: 72).background(Theme.blue, in: RoundedRectangle(cornerRadius: 18))
                        }.buttonStyle(.plain)
                        NavigationLink { BeforeAfterView(jobs: shownJobs) } label: {
                            HStack(spacing: 10) { Image(systemName: "rectangle.split.2x1"); Text("Before / After") }
                                .font(.title3.weight(.bold)).foregroundStyle(Theme.green)
                                .frame(maxWidth: .infinity).frame(height: 72)
                                .background(Theme.green.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))
                                .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.green, lineWidth: 1.5))
                        }.buttonStyle(.plain)
                    }
                    Button { stamp.toggle() } label: {
                        HStack(spacing: 14) {
                            RoundedRectangle(cornerRadius: 8).fill(stamp ? Theme.blue : Color.clear)
                                .overlay(RoundedRectangle(cornerRadius: 8).stroke(stamp ? Theme.blue : Color.secondary, lineWidth: 2))
                                .overlay { if stamp { Image(systemName: "checkmark").font(.headline.weight(.bold)).foregroundStyle(.white) } }
                                .frame(width: 34, height: 34)
                            Text("Stamp date, time & address on new photos").font(.title3.weight(.semibold)).foregroundStyle(.primary)
                                .multilineTextAlignment(.leading)
                        }
                    }.buttonStyle(.plain)
                    Menu {
                        Button("All Jobs") { pick = "" }
                        ForEach(jobs) { j in Button(j.name) { pick = key(j) } }
                    } label: {
                        HStack { Text(pick.isEmpty ? "All Jobs" : (jobs.first { key($0) == pick }?.name ?? "")).font(.title3); Spacer(); Image(systemName: "chevron.down").font(.footnote.weight(.bold)) }
                            .foregroundStyle(.primary).padding(.horizontal, 18).frame(height: 56)
                            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
                            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark), lineWidth: 1))
                    }.menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                    ForEach(shownJobs) { j in
                        if shownJobs.count > 1 { Text(j.name).font(.title2.weight(.heavy)).padding(.top, 10) }
                        let n = (j.photos ?? []).filter { $0.space == nil }.count
                        NavigationLink { PhotosView(job: j, space: nil) } label: {
                            VStack(alignment: .leading, spacing: 8) {
                                Image(systemName: "questionmark.circle").font(.system(size: 34))
                                Text("Unfiled").font(.title2.weight(.heavy))
                                HStack(alignment: .firstTextBaseline, spacing: 8) {
                                    Text("\(n)").font(.system(size: 36, weight: .heavy)).foregroundStyle(n > 0 ? Theme.red : Color.secondary)
                                    Text("TO FILE").font(.headline.weight(.bold)).foregroundStyle(.secondary)
                                }
                            }
                            .foregroundStyle(.primary).padding(16).frame(width: 190, alignment: .leading)
                            .background(Theme.red.opacity(0.06), in: RoundedRectangle(cornerRadius: 22))
                            .overlay(RoundedRectangle(cornerRadius: 22).stroke(Theme.red.opacity(0.6), lineWidth: 1.5))
                        }.buttonStyle(.plain)
                        SpaceGrid(job: j, mode: .photos, scroll: false, showExtras: false)
                    }
                    Color.clear.frame(height: 110)
                }
                .padding(.horizontal, 16).padding(.top, 8)
            }
            .background(Theme.bg(dark))
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
            .shellAdd(symbol: "camera") { picking = true }
            .photosPicker(isPresented: $picking, selection: $picked, matching: .images)
            .onChange(of: picked) { _, items in
                Task {
                    for it in items {
                        if let d = try? await it.loadTransferable(type: Data.self), let j = target {
                            let p = SitePhoto(data: d); p.job = j; context.insert(p)
                        }
                    }
                    picked = []
                }
            }
        }
    }
}

struct PhotoTimeline: View {
    let photos: [SitePhoto]
    @AppStorage("bpDark") private var dark = true
    @State private var open: SitePhoto?
    private let cols = [GridItem(.adaptive(minimum: 100), spacing: 4)]
    private var days: [(Date, [SitePhoto])] {
        let g = Dictionary(grouping: photos) { Calendar.current.startOfDay(for: $0.created) }
        return g.keys.sorted(by: >).map { ($0, g[$0]!) }
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text("Timeline").font(.system(size: 40, weight: .heavy))
                ForEach(days, id: \.0) { d, list in
                    Text(d.formatted(.dateTime.weekday(.wide).month().day().year())).font(.title3.weight(.bold)).foregroundStyle(Theme.blue)
                    LazyVGrid(columns: cols, spacing: 4) {
                        ForEach(list) { p in PhotoThumb(photo: p).onTapGesture { open = p } }
                    }
                }
                if photos.isEmpty { Text("No photos yet.").foregroundStyle(.secondary) }
                Color.clear.frame(height: 110)
            }.padding(.horizontal, 16).padding(.top, 8)
        }
        .background(Theme.bg(dark))
        .navigationDestination(item: $open) { p in MarkupView(data: p.data ?? Data()) { p.data = $0 } }
    }
}

struct BeforeAfterView: View {
    let jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    private var pairs: [(PunchItem, PunchPhoto, PunchPhoto)] {
        jobs.flatMap { $0.punchItems ?? [] }.compactMap { it in
            let ph = (it.photos ?? [])
            guard let b = ph.first(where: { $0.kind == "Before" }), let a = ph.last(where: { $0.kind == "After" || $0.kind == "Completion" }) else { return nil }
            return (it, b, a)
        }
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text("Before / After").font(.system(size: 36, weight: .heavy))
                ForEach(Array(pairs.enumerated()), id: \.offset) { _, t in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(t.0.text).font(.title3.weight(.bold))
                        HStack(spacing: 6) {
                            side("BEFORE", t.1, Theme.red); side("AFTER", t.2, Theme.green)
                        }
                    }
                }
                if pairs.isEmpty { Text("No before/after pairs yet. Add a Before and an After photo to a punch item.").foregroundStyle(.secondary) }
                Color.clear.frame(height: 110)
            }.padding(.horizontal, 16).padding(.top, 8)
        }.background(Theme.bg(dark))
    }
    private func side(_ t: String, _ p: PunchPhoto, _ c: Color) -> some View {
        VStack(spacing: 4) {
            Group {
                if let d = p.data, let img = PhotoThumb.image(d) { img.resizable().scaledToFill() } else { Color.gray.opacity(0.3) }
            }.frame(height: 200).frame(maxWidth: .infinity).clipped().clipShape(RoundedRectangle(cornerRadius: 12))
            Text(t).font(.caption.weight(.heavy)).tracking(1.5).foregroundStyle(c)
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

// MARK: - Finance (matches the web Finance screen)

struct AllMoneyView: View {
    @Query(sort: \Job.created, order: .reverse) private var allJobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @State private var pick: String = ""          // "" = All Jobs
    @State private var path: [Route] = []
    struct Route: Hashable { let job: Job }

    private var jobs: [Job] { pick.isEmpty ? allJobs : allJobs.filter { String($0.created.timeIntervalSince1970) == pick } }
    private func sum(_ f: (Job) -> Double) -> Double { jobs.reduce(0) { $0 + f($1) } }
    private func usd(_ v: Double) -> String { (v < 0 ? "-" : "") + abs(v).formatted(.currency(code: "USD").precision(.fractionLength(0))) }

    private var contract: Double { sum { $0.revisedContract } }
    private var costs: Double { sum { $0.totalCost } }
    private var invoiced: Double { sum { $0.invoiced } }
    private var expenses: Double { sum { $0.expenseTotal } }
    private var subs: Double { sum { $0.contractorTotal } }
    private var left: Double { contract - costs }
    private var margin: Int { contract > 0 ? Int((left / contract * 100).rounded()) : 0 }

    var body: some View {
        NavigationStack(path: $path) {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Finance").font(.system(size: 40, weight: .heavy)).padding(.top, 4)
                    picker
                    Divider()
                    if costs > contract && contract > 0 {
                        banner("Over budget by \(usd(costs - contract)) (costs \(usd(costs)) vs contract \(usd(contract)))", Theme.red)
                    }
                    if invoiced == 0 && costs > 0 {
                        banner("Nothing invoiced yet — \(usd(costs)) in costs, $0 billed", Theme.orange)
                    }
                    HStack(spacing: 12) {
                        tile(usd(contract), "CONTRACT VALUE", Theme.blue)
                        tile(usd(abs(left)), left < 0 ? "OVER BUDGET" : "UNDER BUDGET", left < 0 ? Theme.red : Theme.green, minus: left < 0)
                    }
                    HStack(spacing: 12) {
                        tile(usd(invoiced), "INVOICED", Theme.blue)
                        tile(usd(sum { $0.collected }), "COLLECTED", Theme.blue)
                    }
                    HStack(spacing: 12) {
                        tile(usd(expenses), "EXPENSES", Theme.red)
                        tile(usd(subs), "SUB COSTS", Theme.orange)
                    }
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("Profit Margin").font(.title3).foregroundStyle(.secondary)
                            Spacer()
                            Text("\(margin)%").font(.title3.weight(.heavy)).foregroundStyle(margin < 0 ? Theme.red : Theme.green)
                        }
                        ProgressView(value: Double(max(0, min(100, margin))), total: 100).tint(Theme.green)
                    }
                    .padding(16).background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 18))
                    .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border(dark)))
                    Text("Tap a tile to see what's behind the number.").font(.callout).foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity).multilineTextAlignment(.center).padding(.top, 10)
                    Spacer(minLength: 90)
                }
                .padding(.horizontal, 16)
            }
            .background(Theme.bg(dark))
            .navigationDestination(for: Route.self) { JobDetailView(job: $0.job, start: .money) }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
        }
    }

    private var picker: some View {
        Menu {
            Button("All Jobs") { pick = "" }
            ForEach(allJobs) { j in Button(j.name) { pick = String(j.created.timeIntervalSince1970) } }
        } label: {
            HStack {
                Text(pick.isEmpty ? "All Jobs" : (jobs.first?.name ?? "All Jobs")).font(.title3.weight(.semibold))
                Spacer(); Image(systemName: "chevron.down").font(.headline)
            }
            .padding(.horizontal, 18).frame(minHeight: 54)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Theme.border(dark)))
        }.buttonStyle(.plain)
    }

    private func banner(_ text: String, _ color: Color) -> some View {
        Text(text).font(.title3.weight(.bold)).foregroundStyle(color)
            .padding(16).frame(maxWidth: .infinity, alignment: .leading)
            .background(color.opacity(0.14), in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(color.opacity(0.7)))
    }

    private func tile(_ value: String, _ label: String, _ color: Color, minus: Bool = false) -> some View {
        Button {
            if let j = jobs.count == 1 ? jobs.first : nil { path.append(Route(job: j)) }
        } label: {
            VStack(spacing: 6) {
                Text((minus ? "-" : "") + value).font(.system(size: 28, weight: .heavy)).foregroundStyle(color).minimumScaleFactor(0.6).lineLimit(1)
                Text(label + " ›").font(.callout.weight(.bold)).tracking(1).foregroundStyle(.secondary).minimumScaleFactor(0.7).lineLimit(1)
            }
            .frame(maxWidth: .infinity, minHeight: 84)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border(dark)))
        }.buttonStyle(.plain)
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
        }
    }
}

// MARK: - Calendar (matches the web Calendar screen)

struct CalEvent: Identifiable {
    let id = UUID()
    let date: Date
    let title: String
    let job: String
    let kind: String
    let color: Color
    var time: String = ""
    var appointment: Appointment?
}

struct AllCalendarView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @State private var month = Calendar.current.date(from: Calendar.current.dateComponents([.year, .month], from: Date())) ?? Date()
    @State private var picked: Date?
    @State private var editing: Appointment?
    @State private var request: ApptRequest?

    private var cal: Calendar { Calendar.current }

    static func color(for kind: String) -> Color {
        switch kind {
        case "Due Date": return Theme.red
        case "Delivery": return Theme.orange
        case "Job Start": return Theme.green
        case "Job Due": return Theme.yellow
        case "Contractor": return Theme.purple
        case "Permit": return Theme.brown
        case "Invoice": return Theme.teal
        default: return Theme.lightBlue
        }
    }

    static func hhmm(_ d: Date) -> String {
        let c = Calendar.current.dateComponents([.hour, .minute], from: d)
        if (c.hour ?? 0) == 0 && (c.minute ?? 0) == 0 { return "" }
        return String(format: "%02d:%02d", c.hour ?? 0, c.minute ?? 0)
    }

    private var events: [CalEvent] {
        var out: [CalEvent] = []
        for j in jobs {
            for a in j.appointments ?? [] {
                out.append(CalEvent(date: a.date, title: a.title.isEmpty ? "Appointment" : a.title, job: j.name, kind: a.kind,
                                    color: Self.color(for: a.kind), time: Self.hhmm(a.date), appointment: a))
            }
            if let d = j.startDate { out.append(CalEvent(date: d, title: "Job Starts: \(j.name)", job: j.name, kind: "Job Start", color: Self.color(for: "Job Start"))) }
            if let d = j.completionDate { out.append(CalEvent(date: d, title: "Job Due: \(j.name)", job: j.name, kind: "Job Due", color: Self.color(for: "Job Due"))) }
            for k in j.contractors ?? [] { if let d = k.startDate { out.append(CalEvent(date: d, title: "\(k.name) Starts", job: j.name, kind: "Contractor", color: Self.color(for: "Contractor"))) } }
            for p in j.permits ?? [] { out.append(CalEvent(date: p.expirationDate, title: "\(p.trade) permit expires", job: j.name, kind: "Permit", color: Self.color(for: "Permit"))) }
            for i in j.invoices ?? [] { out.append(CalEvent(date: i.date, title: i.title.isEmpty ? "Invoice" : i.title, job: j.name, kind: "Invoice", color: Self.color(for: "Invoice"))) }
        }
        return out.sorted { $0.date < $1.date }
    }

    private var cells: [Date?] {
        guard let range = cal.range(of: .day, in: .month, for: month) else { return [] }
        let blanks = (cal.component(.weekday, from: month) - cal.firstWeekday + 7) % 7
        var out: [Date?] = Array(repeating: nil, count: blanks)
        for d in range { out.append(cal.date(byAdding: .day, value: d - 1, to: month)) }
        return out
    }

    private func dayEvents(_ day: Date) -> [CalEvent] { events.filter { cal.isDate($0.date, inSameDayAs: day) } }
    private var shown: [CalEvent] {
        if let d = picked { return dayEvents(d) }
        return events.filter { cal.isDate($0.date, equalTo: month, toGranularity: .month) }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    Text("Calendar").font(.system(size: 40, weight: .heavy))
                    monthBar
                    HStack(spacing: 12) {
                        addButton("+ Appointment", Theme.lightBlue, "Appointment")
                        addButton("+ Due Date", Theme.red, "Due Date")
                    }
                    Divider()
                    legend
                    grid
                    Text(picked == nil ? "THIS MONTH" : (picked!.formatted(date: .complete, time: .omitted)).uppercased())
                        .font(.title3.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary).padding(.top, 8)
                    if shown.isEmpty { Text("Nothing here.").foregroundStyle(.secondary) }
                    ForEach(shown) { e in eventCard(e) }
                    Spacer(minLength: 90)
                }
                .padding(.horizontal, 16).padding(.top, 8)
            }
            .background(Theme.bg(dark))
            .navigationDestination(item: $editing) { AppointmentDetail(item: $0) }
            .sheet(item: $request) { AppointmentSheet(req: $0) }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
        }
    }

    private var monthBar: some View {
        HStack {
            square("chevron.left") { shift(-1) }
            Spacer()
            Text(month.formatted(.dateTime.month(.wide).year())).font(.title.weight(.heavy))
            Spacer()
            square("chevron.right") { shift(1) }
        }
    }

    private func square(_ symbol: String, _ tap: @escaping () -> Void) -> some View {
        Button(action: tap) {
            Image(systemName: symbol).font(.headline).frame(width: 44, height: 44)
                .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
        }.buttonStyle(.plain)
    }

    @ViewBuilder private func addButton(_ title: String, _ color: Color, _ kind: String) -> some View {
        let label = Text(title).font(.headline.weight(.heavy)).foregroundStyle(.white)
            .frame(maxWidth: .infinity, minHeight: 46).background(color, in: RoundedRectangle(cornerRadius: 14))
        Button { request = ApptRequest(kind: kind, date: picked ?? Calendar.current.startOfDay(for: Date()), job: jobs.first) } label: { label }.buttonStyle(.plain)
    }

    private var legend: some View {
        let items = ["Appointment", "Due Date", "Delivery", "Job Start", "Job Due", "Contractor", "Permit", "Invoice"]
        return LazyVGrid(columns: [GridItem(.adaptive(minimum: 140), alignment: .leading)], alignment: .leading, spacing: 8) {
            ForEach(items, id: \.self) { k in
                HStack(spacing: 8) { Circle().fill(Self.color(for: k)).frame(width: 14, height: 14); Text(k).font(.callout.weight(.semibold)).foregroundStyle(.secondary) }
            }
        }
    }

    private var grid: some View {
        let cols = Array(repeating: GridItem(.flexible(), spacing: 6), count: 7)
        return LazyVGrid(columns: cols, spacing: 6) {
            ForEach(Array(cal.veryShortWeekdaySymbols.enumerated()), id: \.offset) { _, d in
                Text(d).font(.callout.weight(.bold)).foregroundStyle(.secondary)
            }
            ForEach(Array(cells.enumerated()), id: \.offset) { _, day in
                if let day { cell(day) } else { Color.clear.frame(height: 54) }
            }
        }
    }

    private func cell(_ day: Date) -> some View {
        let evs = dayEvents(day)
        let kinds = Array(Set(evs.map { $0.kind })).sorted().prefix(4)
        let isToday = cal.isDateInToday(day)
        let isPicked = picked.map { cal.isDate($0, inSameDayAs: day) } ?? false
        return Button { picked = isPicked ? nil : cal.startOfDay(for: day) } label: {
            VStack(spacing: 4) {
                Text("\(cal.component(.day, from: day))").font(.headline.weight(.heavy)).foregroundStyle(isToday ? Theme.blue : Color.primary)
                HStack(spacing: 3) { ForEach(Array(kinds), id: \.self) { k in Circle().fill(Self.color(for: k)).frame(width: 8, height: 8) } }.frame(height: 8)
            }
            .frame(maxWidth: .infinity, minHeight: 54)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(isPicked || isToday ? Theme.blue : Theme.border(dark), lineWidth: isPicked || isToday ? 1.5 : 1))
        }.buttonStyle(.plain)
    }

    private func eventCard(_ e: CalEvent) -> some View {
        HStack(spacing: 0) {
            Rectangle().fill(e.color).frame(width: 5)
            VStack(alignment: .leading, spacing: 6) {
                Text(e.title).font(.title3.weight(.heavy)).lineLimit(2)
                Text(e.date.formatted(.dateTime.month(.twoDigits).day(.twoDigits).year()) + (e.time.isEmpty ? "" : " · " + e.time) + " · " + e.job)
                    .font(.callout).foregroundStyle(.secondary)
                if let a = e.appointment {
                    HStack(spacing: 14) {
                        Button { editing = a } label: {
                            Label("Edit", systemImage: "pencil").font(.callout.weight(.bold))
                                .padding(.horizontal, 14).padding(.vertical, 10)
                                .background(Color.primary.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                        }.buttonStyle(.plain)
                        Button { context.delete(a) } label: { Image(systemName: "xmark").foregroundStyle(.secondary) }.buttonStyle(.plain)
                    }
                }
            }
            .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Theme.card(dark))
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border(dark)))
    }

    private func shift(_ by: Int) { if let m = cal.date(byAdding: .month, value: by, to: month) { month = m } }

    private func add(_ kind: String, to job: Job) {
        let a = Appointment(title: kind == "Due Date" ? "New due date" : "New appointment")
        a.kind = kind
        let base = picked ?? cal.startOfDay(for: Date())
        a.date = cal.date(bySettingHour: 9, minute: 0, second: 0, of: base) ?? base
        context.insert(a)
        a.job = job
        editing = a
    }
}


/// The outlined map-pin used in the web header (Feather "map-pin").
struct FeatherPin: Shape {
    func path(in r: CGRect) -> Path {
        let k = min(r.width, r.height) / 24
        func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: r.minX + x * k, y: r.minY + y * k) }
        var path = Path()
        path.move(to: p(21, 10))
        path.addCurve(to: p(12, 23), control1: p(21, 17), control2: p(12, 23))
        path.addCurve(to: p(3, 10), control1: p(12, 23), control2: p(3, 17))
        path.addArc(center: p(12, 10), radius: 9 * k, startAngle: .degrees(180), endAngle: .degrees(0), clockwise: false)
        path.closeSubpath()
        path.addEllipse(in: CGRect(x: r.minX + 9 * k, y: r.minY + 7 * k, width: 6 * k, height: 6 * k))
        return path
    }
}
