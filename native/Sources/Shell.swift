import SwiftUI
import PhotosUI
import SwiftData
#if canImport(UIKit)
import UIKit
#endif

// MARK: - Look (same colors as the web field app)

enum Theme {
    static let blue = Color(red: 0.039, green: 0.518, blue: 1.0)        // #0A84FF
    static let orange = Color(red: 1.0, green: 0.667, blue: 0.2)        // #FFAA33
    /// On iPad/Mac the Command Center uses the web Command Center's navy palette.
    nonisolated(unsafe) static var desk = false
    @discardableResult static func setDesk(_ on: Bool) -> Bool { desk = on; return on }
    private static func hex(_ v: UInt32) -> Color { Color(red: Double((v >> 16) & 255) / 255, green: Double((v >> 8) & 255) / 255, blue: Double(v & 255) / 255) }
    static func bg(_ dark: Bool) -> Color { desk ? hex(dark ? 0x070B22 : 0xEAF0FF) : (dark ? Color(red: 0.059, green: 0.059, blue: 0.059) : Color(red: 0.949, green: 0.969, blue: 1.0)) }
    static func card(_ dark: Bool) -> Color { desk ? hex(dark ? 0x141C4A : 0xFFFFFF) : (dark ? Color(red: 0.102, green: 0.102, blue: 0.102) : .white) }
    static func card2(_ dark: Bool) -> Color { hex(dark ? 0x1B2560 : 0xDDE7FF) }
    static func border(_ dark: Bool) -> Color { desk ? hex(dark ? 0x2C3A8A : 0xB8C8F5) : (dark ? Color(red: 0.165, green: 0.165, blue: 0.165) : Color(red: 0.878, green: 0.878, blue: 0.878)) }
    static func muted(_ dark: Bool) -> Color { hex(dark ? 0x8FA4F0 : 0x3F52C0) }
    static func faint(_ dark: Bool) -> Color { hex(dark ? 0xAABBFF : 0x4A5CC0) }
    static let gold = hex(0xFFB020), sky = hex(0x2EC4FF), deskRed = hex(0xFF4D5E)
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
    @AppStorage("bpZoomPct") private var zoomPct = 100          // 85–180, same as the web apps
    @State private var sizeSheet = false
    @State private var screen: AppScreen = .home
    @State private var menu = false
    @State private var syncNote = false
    @State private var feedbackNote = false
    @StateObject private var shell = ShellState()
    #if os(iOS)
    @Environment(\.horizontalSizeClass) private var hSize
    private var wide: Bool { hSize == .regular }        // iPad full screen → Command Center
    #else
    private var wide: Bool { true }
    #endif

    /// Phone: map the percentage onto Dynamic Type steps.
    private var dynamicSize: DynamicTypeSize {
        switch zoomPct {
        case ..<108: return .large
        case ..<123: return .xLarge
        case ..<138: return .xxLarge
        case ..<153: return .xxxLarge
        case ..<168: return .accessibility1
        default: return .accessibility2
        }
    }
    @State private var pinch: CGFloat = 1
    @AppStorage("bpPinchLock") private var pinchLock = 0
    private var zoom: CGFloat { min(max(CGFloat(zoomPct) / 100 * pinch, 0.85), 1.8) }

    var body: some View {
        if wide {
            // iPad / Mac Command Center: the whole screen scales, like the web Command Center.
            // Pinch with two fingers anywhere to zoom; the A− / A+ panel does the same.
            GeometryReader { g in
                content
                    .frame(width: g.size.width / zoom, height: g.size.height / zoom)
                    .scaleEffect(zoom, anchor: .topLeading)
                    .frame(width: g.size.width, height: g.size.height, alignment: .topLeading)
            }
            .onAppear { pinchLock = 0 }
            .simultaneousGesture(
                MagnifyGesture()
                    .onChanged { v in pinch = v.magnification }
                    .onEnded { v in
                        let nv = Int((Double(zoomPct) * Double(v.magnification) / 5).rounded()) * 5
                        zoomPct = min(180, max(85, nv)); pinch = 1
                    },
                including: pinchLock > 0 ? .subviews : .all
            )
        } else {
            content
        }
    }

    private var content: some View {
        Group {
            let _ = Theme.setDesk(wide)
            if wide {
                CommandCenterView().environmentObject(shell)
                    .tint(Theme.blue)
                    .preferredColorScheme(dark ? .dark : .light)
                    .dynamicTypeSize(.large)
            } else { phoneContent }
        }
    }

    private var phoneContent: some View {
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
            // keep the last rows of every screen scrollable clear of the floating buttons
            .safeAreaInset(edge: .bottom, spacing: 0) { Color.clear.frame(height: 84) }
            .overlay(alignment: .bottomTrailing) {
                FloatBar(showBack: screen != .home)
                    .environment(\.openMenu, { withAnimation(.easeOut(duration: 0.25)) { menu = true } })
                    .environmentObject(shell)
            }
            .onAppear { shell.goHome = { screen = .home }; installScrollWatch() }
            .onChange(of: screen) { _, _ in shell.barHidden = false }

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
        .sheet(isPresented: $sizeSheet) { TextSizePanel(showDone: true).presentationDetents([.height(430)]).preferredColorScheme(dark ? .dark : .light) }
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
    @State private var watcher: ScrollWatcher?
    /// Hides the floating buttons while you scroll down and brings them back when you scroll up.
    /// A passive pan recognizer on the window: it watches touches but never steals them from the scroll view.
    private func installScrollWatch() {
        guard watcher == nil else { return }
        let w = ScrollWatcher { hide in if shell.barHidden != hide { shell.barHidden = hide } }
        watcher = w
        func attach(_ tries: Int) {
            if let win = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).flatMap({ $0.windows }).first(where: { $0.isKeyWindow }) {
                let g = UIPanGestureRecognizer(target: w, action: #selector(ScrollWatcher.pan(_:)))
                g.cancelsTouchesInView = false; g.delaysTouchesBegan = false; g.delaysTouchesEnded = false
                g.delegate = w
                win.addGestureRecognizer(g)
            } else if tries < 10 {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { attach(tries + 1) }
            }
        }
        attach(0)
    }
    #endif

    private var drawer: some View {
        ScrollView(showsIndicators: false) { drawerRows }
            .frame(width: 300)
            .frame(maxHeight: .infinity)
            .background(Theme.card(dark).ignoresSafeArea())
            .overlay(alignment: .trailing) { Rectangle().fill(Theme.border(dark)).frame(width: 1).ignoresSafeArea() }
    }

    private var drawerRows: some View {
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
            Button { withAnimation(.easeOut(duration: 0.25)) { menu = false }; sizeSheet = true } label: {
                tool(icon: nil, aa: true, title: "Text size", sub: "\(zoomPct)%")
            }.buttonStyle(.plain)
            Button { dark.toggle() } label: {
                tool(icon: "circle.lefthalf.filled", aa: false, title: "Light / Dark", sub: dark ? "Dark" : "Light")
            }.buttonStyle(.plain)
            row(.search)
            row(.calendar)
            Button { syncNote = true } label: { tool(icon: "arrow.triangle.2.circlepath", aa: false, title: "Sync", sub: "iCloud · automatic") }.buttonStyle(.plain)
            Button { feedbackNote = true } label: { tool(icon: "bubble.left", aa: false, title: "Send feedback", sub: "") }.buttonStyle(.plain)
        }
        .padding(12)
        .frame(width: 300, alignment: .leading)
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
    private var active: Job? { activeKey.isEmpty ? nil : jobs.first { key($0) == activeKey } }   // blank until you pick one
    private var version: String { "v" + ((Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "") }

    var body: some View {
        NavigationStack(path: $path) {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    top
                    if !jobs.isEmpty { picker(active) }
                    if let job = active {
                        Divider().padding(.horizontal, -16)
                        siteCard(job)
                        quickTiles(job)
                        attention(job)
                    } else if jobs.isEmpty {
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
                Spacer(minLength: 8)
                Text(greeting)
                    .font(.system(size: 40, weight: .regular))
                    .minimumScaleFactor(0.5).lineLimit(1).multilineTextAlignment(.trailing)
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

    private func picker(_ job: Job?) -> some View {
        Menu {
            ForEach(jobs) { j in Button(j.name) { activeKey = key(j) } }
        } label: {
            HStack(spacing: 12) {
                Image(systemName: "mappin.and.ellipse").font(.title3).foregroundStyle(Theme.blue)
                Text("ON SITE").font(.subheadline.weight(.heavy)).tracking(1.5).foregroundStyle(.secondary)
                Text(job?.name ?? "Select a job").font(.title3.weight(.bold)).foregroundStyle(job == nil ? Color.secondary : Theme.blue).lineLimit(1)
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
                            NavigationLink { AllSpacesView(startJob: job) } label: {
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
    @AppStorage("bpActiveJob") private var pick = ""   // shared: the job you chose stays chosen everywhere ("" = All Jobs)
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
                        NavigationLink { BeforeAfterView(jobs: shownJobs) } label: {
                            HStack(spacing: 10) { Image(systemName: "rectangle.split.2x1"); Text("Before / After").lineLimit(1).minimumScaleFactor(0.7) }
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
                        if n > 0 { NavigationLink { PhotosView(job: j, space: nil) } label: {
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
                        }.buttonStyle(.plain) }
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
        .navigationDestination(item: $open) { p in PhotoPager(photos: days.flatMap { $0.1 }, start: p) }
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
                if p.data != nil { ThumbImage(data: p.data, px: 700) } else { Color.gray.opacity(0.3) }
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
    @AppStorage("bpActiveJob") private var pick: String = ""   // shared active job ("" = All Jobs)
    @State private var path: [Route] = []
    struct Route: Hashable { let job: Job; var page = "Overview" }
    struct FinItem: Identifiable { let kind: String; let job: Job?; var id: String { kind } }
    @AppStorage("bpActiveJob") private var activeKey = ""
    @State private var fin: FinItem?

    private var jobs: [Job] { pick.isEmpty ? allJobs : allJobs.filter { String($0.created.timeIntervalSince1970) == pick } }
    private func sum(_ f: (Job) -> Double) -> Double { jobs.reduce(0) { $0 + f($1) } }
    private func usd(_ v: Double) -> String { (v < 0 ? "-" : "") + abs(v).formatted(.currency(code: "USD").precision(.fractionLength(0))) }

    var body: some View {
        NavigationStack(path: $path) {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Finance").font(.system(size: 40, weight: .heavy)).padding(.top, 4)
                    picker
                    Divider()
                    ForEach(jobs) { j in
                        if jobs.count > 1 { Text(j.name).font(.title2.weight(.heavy)).padding(.top, 10) }
                        block(j)
                    }
                    Text("Tap a tile to see what's behind the number.").font(.callout).foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity).multilineTextAlignment(.center).padding(.top, 10)
                    Spacer(minLength: 90)
                }
                .padding(.horizontal, 16)
            }
            .background(Theme.bg(dark))
            .navigationDestination(for: Route.self) { JobDetailView(job: $0.job, start: .money, moneyPage: $0.page) }
            .shellAdd { fin = FinItem(kind: "picker", job: nil) }
            .sheet(item: $fin) { k in
                switch k.kind {
                case "picker":
                    FinanceAddSheet(jobs: allJobs, initial: jobs.count == 1 ? jobs.first : (allJobs.first { String($0.created.timeIntervalSince1970) == activeKey } ?? allJobs.first { $0.isActive })) { j, what in
                        fin = FinItem(kind: what, job: j)
                    }
                case "Expense": if let t = k.job { ExpenseSheet(job: t) }
                case "Contractor": if let t = k.job { ContractorSheet(job: t) }
                case "Change order": if let t = k.job { ChangeOrderSheet(job: t) }
                case "Permit": if let t = k.job { PermitSheet(job: t) }
                case "Delivery": if let t = k.job { DeliverySheet(job: t) }
                default: if let t = k.job { InvoiceSheet(job: t) }
                }
            }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
        }
    }

    /// One job's finance tiles.
    @ViewBuilder private func block(_ j: Job) -> some View {
        let contract = j.revisedContract, costs = j.totalCost, invoiced = j.invoiced
        let left = contract - costs
        let margin = contract > 0 ? Int((left / contract * 100).rounded()) : 0
        VStack(alignment: .leading, spacing: 12) {
            if costs > contract && contract > 0 {
                banner("Over budget by \(usd(costs - contract)) (costs \(usd(costs)) vs contract \(usd(contract)))", Theme.red)
            }
            if invoiced == 0 && costs > 0 {
                banner("Nothing invoiced yet — \(usd(costs)) in costs, $0 billed", Theme.orange)
            }
            HStack(spacing: 12) {
                tile(j, usd(contract), "CONTRACT VALUE", Theme.blue, page: "Overview")
                tile(j, usd(abs(left)), left < 0 ? "OVER BUDGET" : "UNDER BUDGET", left < 0 ? Theme.red : Theme.green, minus: left < 0, page: "Overview")
            }
            HStack(spacing: 12) {
                tile(j, usd(invoiced), "INVOICED", Theme.blue, page: "Invoices")
                tile(j, usd(j.collected), "COLLECTED", Theme.blue, page: "Invoices")
            }
            HStack(spacing: 12) {
                tile(j, usd(j.expenseTotal), "EXPENSES", Theme.red, page: "Expenses")
                tile(j, usd(j.contractorTotal), "SUB COSTS", Theme.orange, page: "Contractors")
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

    private func tile(_ j: Job, _ value: String, _ label: String, _ color: Color, minus: Bool = false, page: String = "Overview") -> some View {
        Button { path.append(Route(job: j, page: page)) } label: {
            VStack(spacing: 6) {
                Text((minus ? "-" : "") + value).font(.system(size: 28, weight: .heavy)).foregroundStyle(color).minimumScaleFactor(0.6).lineLimit(1)
                Text(label + " ›").font(.callout.weight(.bold)).tracking(0.3).foregroundStyle(.secondary).minimumScaleFactor(0.7).lineLimit(1)
            }
            .frame(maxWidth: .infinity, minHeight: 84)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(Theme.border(dark)))
        }.buttonStyle(.plain)
    }
}

// MARK: - Search (jobs, punch items, notes)

struct SearchView: View {
    var initial: String = ""
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @State private var q = ""
    @State private var path: [Hit] = []
    @FocusState private var focused: Bool

    struct Hit: Identifiable, Hashable {
        let id = UUID()
        let type: String, symbol: String, title: String, sub: String
        let job: Job
        let start: JobTab
        static func == (a: Hit, b: Hit) -> Bool { a.id == b.id }
        func hash(into h: inout Hasher) { h.combine(id) }
    }

    private var term: String { q.trimmingCharacters(in: .whitespaces).lowercased() }
    private func m(_ s: String) -> Bool { s.lowercased().contains(term) }
    private func usd(_ v: Double) -> String { v.formatted(.currency(code: "USD").precision(.fractionLength(0))) }

    private var hits: [Hit] {
        guard !term.isEmpty else { return [] }
        var out: [Hit] = []
        for j in jobs where m(j.name) || m(j.client) || m(j.address) {
            out.append(Hit(type: "Job", symbol: "briefcase", title: j.name, sub: [j.client, j.address].filter { !$0.isEmpty }.joined(separator: " · "), job: j, start: .spaces))
        }
        for j in jobs {
            for c in j.contractors ?? [] where m(c.name) || m(c.trade) {
                out.append(Hit(type: "Contractor", symbol: "person.2", title: c.name, sub: c.trade, job: j, start: .money))
            }
            for e in j.expenses ?? [] where m(e.title) || m(e.vendor) {
                out.append(Hit(type: "Expense", symbol: "receipt", title: e.title, sub: (e.vendor.isEmpty ? "" : e.vendor + " · ") + usd(e.amount), job: j, start: .money))
            }
            for i in j.invoices ?? [] where m(i.title) {
                out.append(Hit(type: "Invoice", symbol: "doc.text", title: i.title, sub: usd(i.amount), job: j, start: .money))
            }
            for p in j.punchItems ?? [] where m(p.text) {
                out.append(Hit(type: "Punchlist", symbol: "checkmark.square", title: p.text, sub: j.name, job: j, start: .spaces))
            }
            for p in j.permits ?? [] where m(p.trade) || m(p.number) {
                out.append(Hit(type: "Permit", symbol: "checkmark.seal", title: p.trade + (p.number.isEmpty ? "" : " #" + p.number), sub: j.name, job: j, start: .money))
            }
            for n in j.notes ?? [] where m(n.title) || m(n.text) {
                out.append(Hit(type: "Note", symbol: "note.text", title: n.title.isEmpty ? n.text : n.title, sub: j.name, job: j, start: .spaces))
            }
        }
        return out
    }

    var body: some View {
        NavigationStack(path: $path) {
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Search").font(.system(size: 40, weight: .heavy)).padding(.top, 4)
                    TextField("SEARCH", text: $q)
                        .textFieldStyle(.plain).font(.title3).focused($focused)
                        .padding(.horizontal, 16).frame(height: 54)
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark)))
                    let r = hits
                    if term.isEmpty {
                        note("Start typing to search everything — jobs, contractors, expenses, invoices, checklist items, permits.")
                    } else if r.isEmpty {
                        note("No matches for \"\(q)\"")
                    } else {
                        ForEach(r.prefix(50)) { h in
                            Button { path.append(h) } label: {
                                HStack(spacing: 12) {
                                    Image(systemName: h.symbol).font(.title3).foregroundStyle(Theme.blue).frame(width: 30)
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(h.type.uppercased()).font(.footnote.weight(.heavy)).tracking(1).foregroundStyle(.secondary)
                                        Text(h.title).font(.headline).lineLimit(2).multilineTextAlignment(.leading)
                                        if !h.sub.isEmpty { Text(h.sub).font(.callout).foregroundStyle(.secondary).lineLimit(1) }
                                    }
                                    Spacer(minLength: 0)
                                    Image(systemName: "chevron.right").font(.footnote).foregroundStyle(.tertiary)
                                }
                                .padding(.horizontal, 14).padding(.vertical, 12)
                                .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
                                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark)))
                            }.buttonStyle(.plain)
                        }
                    }
                    Spacer(minLength: 90)
                }
                .padding(.horizontal, 16)
            }
            .background(Theme.bg(dark))
            .navigationDestination(for: Hit.self) { JobDetailView(job: $0.job, start: $0.start) }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
        }
        .onAppear { if q.isEmpty { q = initial } }
        .onChange(of: initial) { _, v in q = v }
    }

    private func note(_ t: String) -> some View {
        Text(t).font(.callout).foregroundStyle(.secondary).frame(maxWidth: .infinity).multilineTextAlignment(.center).padding(.top, 30)
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
                    if Theme.desk {
                        deskHeader
                    } else {
                        Text("Calendar").font(.system(size: 40, weight: .heavy))
                        monthBar
                        HStack(spacing: 12) {
                            addButton("+ Appointment", Theme.lightBlue, "Appointment")
                            addButton("+ Due Date", Theme.red, "Due Date")
                        }
                        Divider()
                    }
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

    /// Command Center header, same arrangement as the web: title + date on the left, month nav and add buttons on the right.
    private var deskHeader: some View {
        let count = events.filter { cal.isDate($0.date, equalTo: month, toGranularity: .month) }.count
        return HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text("Calendar").font(.system(size: 40, weight: .heavy)).foregroundStyle(Theme.lightBlue)
                Text(Date().formatted(.dateTime.month(.twoDigits).day(.twoDigits).year()) + " · " + Date().formatted(date: .omitted, time: .shortened))
                    .font(.system(size: 15, weight: .heavy)).foregroundStyle(Theme.sky)
                Text("\(count) event\(count == 1 ? "" : "s") this month").font(.system(size: 15, weight: .semibold)).foregroundStyle(Theme.muted(dark))
            }
            Spacer(minLength: 8)
            HStack(spacing: 10) {
                square("chevron.left") { shift(-1) }
                Text(month.formatted(.dateTime.month(.wide).year())).font(.system(size: 17, weight: .heavy))
                    .padding(.horizontal, 22).frame(height: 44)
                    .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
                square("chevron.right") { shift(1) }
                pill("+ Add Appointment", Theme.sky, "Appointment")
                pill("+ Add Due Date", Theme.deskRed, "Due Date")
            }
        }
    }

    private func pill(_ title: String, _ color: Color, _ kind: String) -> some View {
        Button { request = ApptRequest(kind: kind, date: picked ?? Calendar.current.startOfDay(for: Date()), job: jobs.first) } label: {
            Text(title).font(.system(size: 17, weight: .heavy)).foregroundStyle(.white).lineLimit(1)
                .padding(.horizontal, 22).frame(height: 44).background(color, in: RoundedRectangle(cornerRadius: 12))
        }.buttonStyle(.plain)
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
        return LazyVGrid(columns: [GridItem(.adaptive(minimum: Theme.desk ? 150 : 140), alignment: .leading)], alignment: .leading, spacing: 8) {
            ForEach(items, id: \.self) { k in
                HStack(spacing: 8) { Circle().fill(Self.color(for: k)).frame(width: Theme.desk ? 13 : 14, height: Theme.desk ? 13 : 14); Text(k).lineLimit(1).fixedSize().font(Theme.desk ? .system(size: 15, weight: .heavy) : .callout.weight(.semibold)).foregroundStyle(Theme.desk ? Theme.muted(dark) : .secondary) }
            }
        }
    }

    private var grid: some View {
        let cols = Array(repeating: GridItem(.flexible(), spacing: 6), count: 7)
        return LazyVGrid(columns: cols, spacing: 6) {
            ForEach(Array((Theme.desk ? cal.shortWeekdaySymbols.map { $0.uppercased() } : cal.veryShortWeekdaySymbols).enumerated()), id: \.offset) { _, d in
                Text(d).font(.callout.weight(.bold)).foregroundStyle(.secondary)
            }
            ForEach(Array(cells.enumerated()), id: \.offset) { _, day in
                if let day { cell(day) } else { Color.clear.frame(height: Theme.desk ? 92 : 54) }
            }
        }
    }

    /// Command Center day cell: day number plus colored event chips, like the web.
    private func deskCell(_ day: Date) -> some View {
        let evs = dayEvents(day)
        let isToday = cal.isDateInToday(day)
        let isPicked = picked.map { cal.isDate($0, inSameDayAs: day) } ?? false
        return Button { picked = isPicked ? nil : cal.startOfDay(for: day) } label: {
            VStack(alignment: .leading, spacing: 3) {
                Text("\(cal.component(.day, from: day))").font(.system(size: 15, weight: .heavy)).foregroundStyle(isToday ? Theme.sky : Color.primary)
                ForEach(evs.prefix(2)) { e in
                    Text(e.title).font(.system(size: 11, weight: .heavy)).foregroundStyle(.white).lineLimit(1)
                        .padding(.horizontal, 5).padding(.vertical, 2).frame(maxWidth: .infinity, alignment: .leading)
                        .background(e.color, in: RoundedRectangle(cornerRadius: 4))
                }
                if evs.count > 2 { Text("+\(evs.count - 2) more").font(.system(size: 11, weight: .bold)).foregroundStyle(Theme.muted(dark)) }
                Spacer(minLength: 0)
            }
            .padding(6)
            .frame(maxWidth: .infinity, minHeight: 92, alignment: .topLeading)
            .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(isPicked || isToday ? Theme.sky : Theme.border(dark), lineWidth: isPicked || isToday ? 1.5 : 1))
        }.buttonStyle(.plain)
    }

    @ViewBuilder private func cell(_ day: Date) -> some View {
        if Theme.desk { deskCell(day) } else { phoneCell(day) }
    }

    private func phoneCell(_ day: Date) -> some View {
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

// MARK: - Spaces (all jobs) — Area / Trade views, opened from Punch → Areas

private func tradeColor(_ t: String) -> Color {
    switch t {
    case "Plumbing": return Theme.blue
    case "Electrical": return Theme.yellow
    case "Carpentry": return Theme.brown
    case "HVAC": return Theme.teal
    case "Masonry": return Theme.orange
    case "Drywall": return Theme.lightBlue
    case "Painting": return Theme.purple
    case "Tile/Flooring": return Theme.green
    case "Roofing": return Theme.red
    case "Demo": return .pink
    case "Protection": return .indigo
    default: return .gray
    }
}

struct AllSpacesView: View {
    @Environment(\.dismiss) private var dismiss
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    var startJob: Job? = nil
    @AppStorage("bpActiveJob") private var jobKey = ""   // shared active job ("" = All Jobs)
    @State private var mode = "area"        // area | trade
    @State private var inOut = "All"        // All | Inside | Outside
    @State private var addJob: Job?
    @State private var needJob = false
    @State private var tradeSheet: TradeRef?
    @State private var started = false
    @State private var table = false

    struct TradeRef: Identifiable { let id: String }

    private func key(_ j: Job) -> String { String(j.created.timeIntervalSince1970) }
    private var scopeJobs: [Job] { jobs.filter { jobKey.isEmpty || key($0) == jobKey } }
    private var jobTitle: String { jobs.first { key($0) == jobKey }?.name ?? "All Jobs" }
    private func inScope(_ exterior: Bool) -> Bool {
        inOut == "All" || (inOut == "Outside") == exterior
    }
    private var spaces: [Space] {
        scopeJobs.flatMap { $0.spaces ?? [] }.filter { inScope($0.isExterior) }
            .sorted { $0.openCount != $1.openCount ? $0.openCount > $1.openCount : $0.name.localizedCompare($1.name) == .orderedAscending }
    }
    private var items: [PunchItem] {
        scopeJobs.flatMap { $0.punchItems ?? [] }.filter { inScope($0.space?.isExterior ?? false) }
    }
    private var byTrade: [(trade: String, items: [PunchItem])] {
        Dictionary(grouping: items) { $0.trade.isEmpty ? "Other" : $0.trade }
            .map { (trade: $0.key, items: $0.value) }
            .sorted { a, b in
                let ao = a.items.filter { !$0.done }.count, bo = b.items.filter { !$0.done }.count
                return ao != bo ? ao > bo : a.trade < b.trade
            }
    }
    private var subtitle: String {
        if mode == "trade" { return "\(byTrade.count) trade\(byTrade.count == 1 ? "" : "s") · \(items.count) items" }
        let open = spaces.reduce(0) { $0 + $1.openCount }
        return "\(spaces.count) area\(spaces.count == 1 ? "" : "s") · \(open) open"
    }
    private var cols: [GridItem] { Theme.desk ? [GridItem(.adaptive(minimum: 210), spacing: 12)] : [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)] }

    // Command Center shows this screen on its own (no parent stack), so give it one — otherwise the space tiles can't open.
    var body: some View {
        if Theme.desk { NavigationStack { page } } else { page }
    }

    private var page: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                if Theme.desk {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("Spaces").font(.system(size: 40, weight: .heavy)).foregroundStyle(Theme.gold)
                            Text(Date().formatted(.dateTime.month(.twoDigits).day(.twoDigits).year()) + " · " + Date().formatted(date: .omitted, time: .shortened))
                                .font(.system(size: 15, weight: .heavy)).foregroundStyle(Theme.sky)
                            Text(subtitle).font(.system(size: 15, weight: .semibold)).foregroundStyle(Theme.muted(dark))
                        }
                        Spacer()
                        Button { startAdd() } label: {
                            Text("+ New Space").font(.system(size: 17, weight: .heavy)).foregroundStyle(.primary)
                                .padding(.horizontal, 22).frame(height: 44)
                                .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 12))
                                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
                        }.buttonStyle(.plain)
                    }
                } else {
                    Button { dismiss() } label: {
                        HStack(spacing: 6) { Image(systemName: "chevron.left").font(.title3.weight(.semibold)); Text("Punch").font(.title3.weight(.semibold)) }
                            .foregroundStyle(Theme.blue)
                    }.buttonStyle(.plain)
                    TopBar(title: "Spaces", sub: subtitle)
                }
                controls
                if mode == "trade" { tradeGrid } else { areaGrid }
                Color.clear.frame(height: 110)
            }
            .padding(.horizontal, 16).padding(.top, 8)
        }
        .background(Theme.bg(dark))
        #if os(iOS)
        .toolbar(.hidden, for: .navigationBar)
        #endif
        .onAppear { if !started { started = true; if let startJob { jobKey = key(startJob) } } }
        .shellAdd { startAdd() }
        .sheet(item: $addJob) { AddSpacesSheet(job: $0) }
        .sheet(item: $tradeSheet) { t in TradeCallSheet(trade: t.id, items: byTrade.first { $0.trade == t.id }?.items ?? []) }
        .alert("Pick a job first", isPresented: $needJob) { Button("OK", role: .cancel) {} } message: { Text("Choose a job in the filter above, then tap + to add spaces.") }
    }

    private func startAdd() {
        if let j = jobs.first(where: { key($0) == jobKey }) { addJob = j }
        else if jobs.count == 1 { addJob = jobs.first }
        else if jobs.isEmpty { needJob = true }
        else { needJob = true }
    }

    private var controls: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                Menu {
                    Button("All Jobs") { jobKey = "" }
                    ForEach(jobs) { j in Button(j.name) { jobKey = key(j) } }
                } label: {
                    HStack { Text(jobTitle).font(.headline.weight(.semibold)).lineLimit(1); Spacer(); Image(systemName: "chevron.down").font(.footnote.weight(.bold)) }
                        .foregroundStyle(.primary).padding(.horizontal, 14).frame(height: 46)
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark), lineWidth: 1))
                }
                .menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                HStack(spacing: 3) { seg("Area", "area"); seg("Trade", "trade") }
                    .padding(3).background(Theme.border(dark).opacity(0.5), in: RoundedRectangle(cornerRadius: 12))
            }
            HStack(spacing: 8) {
                tab("All", "All"); tab("Inside", "Inside"); tab("Outside", "Outside")
                if Theme.desk && mode == "area" {
                    HStack(spacing: 3) { layoutSeg("square.grid.2x2", "Grid", false); layoutSeg("tablecells", "Table", true) }
                        .padding(3).background(Theme.border(dark).opacity(0.5), in: RoundedRectangle(cornerRadius: 12))
                }
            }
        }
    }

    private func layoutSeg(_ icon: String, _ label: String, _ v: Bool) -> some View {
        Button { table = v } label: {
            HStack(spacing: 6) { Image(systemName: icon).font(.system(size: 15, weight: .bold)); Text(label).font(.system(size: 15, weight: .heavy)).lineLimit(1) }
                .fixedSize().foregroundStyle(table == v ? Theme.sky : Theme.muted(dark))
                .padding(.horizontal, 14).frame(height: 38)
                .background(table == v ? Theme.card(dark) : .clear, in: RoundedRectangle(cornerRadius: 9))
        }.buttonStyle(.plain)
    }

    /// Command Center table layout: one row per space.
    private var spaceTable: some View {
        VStack(spacing: 0) {
            HStack {
                Text("SPACE").frame(maxWidth: .infinity, alignment: .leading)
                Text("LEVEL").frame(width: 120, alignment: .leading)
                Text("JOB").frame(width: 180, alignment: .leading)
                Text("OPEN").frame(width: 70, alignment: .trailing)
                Text("DONE").frame(width: 70, alignment: .trailing)
                Text("PHOTOS").frame(width: 80, alignment: .trailing)
            }
            .font(.system(size: 13, weight: .heavy)).tracking(0.8).foregroundStyle(Theme.muted(dark)).padding(.horizontal, 16).padding(.vertical, 10)
            Divider()
            ForEach(spaces) { sp in
                if let j = sp.job {
                    NavigationLink { PunchListView(job: j, space: sp) } label: {
                        HStack {
                            HStack(spacing: 10) { SpaceIcon(name: sp.name, symbol: sp.symbol, size: 22).frame(width: 28); Text(sp.name).font(.system(size: 16, weight: .heavy)) }
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Text(sp.level.isEmpty ? (sp.isExterior ? "Outside" : "—") : sp.level).frame(width: 120, alignment: .leading).foregroundStyle(Theme.sky)
                            Text(j.name).lineLimit(1).frame(width: 180, alignment: .leading).foregroundStyle(Theme.muted(dark))
                            Text("\(sp.openCount)").frame(width: 70, alignment: .trailing).foregroundStyle(sp.openCount == 0 ? Theme.muted(dark) : Theme.deskRed)
                            Text("\(sp.doneCount)").frame(width: 70, alignment: .trailing).foregroundStyle(sp.doneCount == 0 ? Theme.muted(dark) : Theme.green)
                            Text("\(sp.photoCount)").frame(width: 80, alignment: .trailing).foregroundStyle(Theme.sky)
                        }
                        .font(.system(size: 15, weight: .bold)).padding(.horizontal, 16).padding(.vertical, 12).contentShape(Rectangle())
                    }.buttonStyle(.plain)
                    Divider()
                }
            }
        }
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.border(dark)))
    }

    private func seg(_ label: String, _ v: String) -> some View {
        Button { mode = v } label: {
            Text(label).font(.subheadline.weight(.heavy)).foregroundStyle(mode == v ? Color.primary : .secondary)
                .padding(.horizontal, 14).frame(height: 38)
                .background(mode == v ? Theme.card(dark) : .clear, in: RoundedRectangle(cornerRadius: 9))
        }.buttonStyle(.plain)
    }
    private func tab(_ label: String, _ v: String) -> some View {
        Button { inOut = v } label: {
            Text(label).font(.headline.weight(.heavy)).foregroundStyle(inOut == v ? Theme.blue : .secondary)
                .frame(maxWidth: .infinity).frame(height: 42)
                .background(inOut == v ? Theme.blue.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 10))
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(inOut == v ? Theme.blue : Theme.border(dark), lineWidth: 1.5))
        }.buttonStyle(.plain)
    }

    private var areaGrid: some View {
        Group {
            if spaces.isEmpty {
                VStack(spacing: 10) {
                    Image(systemName: "house").font(.system(size: 40)).foregroundStyle(.secondary)
                    Text("No \(inOut == "All" ? "areas" : inOut.lowercased() + " areas") yet").font(.title3.weight(.bold))
                    Text("Tap + to pick from the preset list").foregroundStyle(.secondary)
                    Button { startAdd() } label: {
                        Text("+ Add Spaces").font(.headline.weight(.heavy)).foregroundStyle(.white)
                            .padding(.horizontal, 22).frame(height: 48).background(Theme.blue, in: RoundedRectangle(cornerRadius: 12))
                    }.buttonStyle(.plain)
                }.frame(maxWidth: .infinity).padding(.top, 30)
            } else {
                if Theme.desk { if table { spaceTable } else { levelSections } } else {
                LazyVGrid(columns: cols, spacing: 10) {
                    ForEach(spaces) { s in
                        if let j = s.job {
                            NavigationLink { PunchListView(job: j, space: s) } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    SpaceTile(space: s, mode: .punch)
                                    if jobKey.isEmpty { Text(j.name).font(.caption.weight(.semibold)).foregroundStyle(.secondary).lineLimit(1).padding(.leading, 6) }
                                }
                            }.buttonStyle(.plain)
                        }
                    }
                    Button { startAdd() } label: {
                        RoundedRectangle(cornerRadius: 22).strokeBorder(Theme.blue.opacity(0.5), style: StrokeStyle(lineWidth: 1.5, dash: [6, 5]))
                            .frame(minHeight: 150)
                            .overlay(Image(systemName: "plus").font(.system(size: 34, weight: .light)).foregroundStyle(Theme.blue))
                    }.buttonStyle(.plain)
                }
                }
            }
        }
    }

    /// Command Center: spaces grouped under their level, like the web ("BASEMENT  2 spaces").
    private var levelSections: some View {
        let order = ["Basement", "Level 1", "Level 2", "Level 3", "Level 4", "Attic", "Roof", "Outside"]
        let groups = Dictionary(grouping: spaces) { $0.level.isEmpty ? (($0.isExterior) ? "Outside" : "Other") : $0.level }
        let keys = groups.keys.sorted { a, b in
            let ia = order.firstIndex(of: a) ?? 99, ib = order.firstIndex(of: b) ?? 99
            return ia != ib ? ia < ib : a < b
        }
        return VStack(alignment: .leading, spacing: 18) {
            ForEach(keys, id: \.self) { k in
                let list = (groups[k] ?? []).sorted { $0.order != $1.order ? $0.order < $1.order : $0.name < $1.name }
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 8) {
                        Text(k.uppercased()).font(.system(size: 15, weight: .heavy)).tracking(0.8).foregroundStyle(k == "Basement" ? Theme.brown : Theme.sky)
                        Text("\(list.count) space\(list.count == 1 ? "" : "s")").font(.system(size: 14, weight: .bold)).foregroundStyle(Theme.muted(dark))
                        Spacer()
                    }
                    Rectangle().fill((k == "Basement" ? Theme.brown : Theme.sky).opacity(0.6)).frame(height: 2)
                    LazyVGrid(columns: cols, spacing: 12) {
                        ForEach(list) { s in
                            if let j = s.job {
                                NavigationLink { PunchListView(job: j, space: s) } label: {
                                    VStack(alignment: .leading, spacing: 4) {
                                        SpaceTile(space: s, mode: .punch)
                                        if jobKey.isEmpty { Text(j.name).font(.caption.weight(.semibold)).foregroundStyle(.secondary).lineLimit(1).padding(.leading, 6) }
                                    }
                                }.buttonStyle(.plain)
                            }
                        }
                    }
                }
            }
            Button { startAdd() } label: {
                Text("+ Add Spaces").font(.system(size: 17, weight: .heavy)).foregroundStyle(.white)
                    .padding(.horizontal, 26).frame(height: 48).background(Theme.gold, in: RoundedRectangle(cornerRadius: 12))
            }.buttonStyle(.plain)
        }
    }

    private var tradeGrid: some View {
        Group {
            if byTrade.isEmpty {
                VStack(spacing: 10) {
                    Image(systemName: "wrench.and.screwdriver").font(.system(size: 40)).foregroundStyle(.secondary)
                    Text("No items yet").font(.title3.weight(.bold))
                    Text("Add punch items and they group by trade here").foregroundStyle(.secondary).multilineTextAlignment(.center)
                }.frame(maxWidth: .infinity).padding(.top, 30)
            } else {
                LazyVGrid(columns: cols, spacing: 10) {
                    ForEach(byTrade, id: \.trade) { g in
                        let done = g.items.filter { $0.done }.count, open = g.items.count - done
                        let col = tradeColor(g.trade)
                        Button { tradeSheet = TradeRef(id: g.trade) } label: {
                            VStack(alignment: .leading, spacing: 8) {
                                Image(systemName: Trades.symbol(g.trade)).font(.system(size: 28)).foregroundStyle(col)
                                Text(g.trade).font(.headline.weight(.heavy)).foregroundStyle(col).lineLimit(1).minimumScaleFactor(0.8)
                                Spacer(minLength: 0)
                                HStack(alignment: .firstTextBaseline, spacing: 4) {
                                    Text("\(open)").font(.system(size: 28, weight: .black)).foregroundStyle(open == 0 ? Color.secondary : Theme.red)
                                    Text("OPEN").font(.caption.weight(.bold)).foregroundStyle(.secondary)
                                    Spacer()
                                    Text("\(done)").font(.system(size: 28, weight: .black)).foregroundStyle(done == 0 ? Color.secondary : Theme.green)
                                    Text("DONE").font(.caption.weight(.bold)).foregroundStyle(.secondary)
                                }.lineLimit(1).minimumScaleFactor(0.7)
                                Capsule().fill(Color.primary.opacity(0.12)).frame(height: 5)
                                    .overlay(alignment: .leading) {
                                        GeometryReader { p in Capsule().fill(col).frame(width: p.size.width * (g.items.isEmpty ? 0 : Double(done) / Double(g.items.count))) }
                                    }
                            }
                            .padding(14).frame(maxWidth: .infinity, minHeight: 150, alignment: .leading)
                            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 22))
                            .overlay(alignment: .leading) { Rectangle().fill(col).frame(width: 4).clipShape(RoundedRectangle(cornerRadius: 2)).padding(.vertical, 18) }
                            .overlay(RoundedRectangle(cornerRadius: 22).stroke(Theme.border(dark), lineWidth: 1.5))
                        }.buttonStyle(.plain)
                    }
                }
            }
        }
    }
}

/// The "sub call sheet": every punch item for one trade, with the job and space it belongs to.
struct TradeCallSheet: View {
    @AppStorage("bpDark") private var dark = true
    let trade: String
    let items: [PunchItem]
    var body: some View {
        SheetFrame(title: trade) {
            let open = items.filter { !$0.done }.count
            Text("\(open) open · \(items.count - open) done").foregroundStyle(.secondary)
            ForEach(items.sorted { !$0.done && $1.done }) { it in
                HStack(alignment: .top, spacing: 12) {
                    Button { it.done.toggle(); it.completed = it.done ? Date() : nil } label: {
                        Image(systemName: it.done ? "checkmark.square.fill" : "square").font(.title2)
                            .foregroundStyle(it.done ? Theme.green : .secondary)
                    }.buttonStyle(.plain)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(it.text).font(.headline).strikethrough(it.done).foregroundStyle(it.done ? .secondary : .primary)
                        Text((it.job?.name ?? "") + " · " + (it.space?.name ?? "General")).font(.subheadline).foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(14).frame(maxWidth: .infinity, alignment: .leading)
                .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 14))
            }
            if items.isEmpty { Text("Nothing here.").foregroundStyle(.secondary) }
        }
    }
}


#if os(iOS)
final class ScrollWatcher: NSObject, UIGestureRecognizerDelegate {
    let onChange: (Bool) -> Void
    init(_ f: @escaping (Bool) -> Void) { onChange = f }
    @objc func pan(_ g: UIPanGestureRecognizer) {
        guard g.state == .changed else { return }
        let v = g.velocity(in: g.view)
        guard abs(v.y) > abs(v.x) * 1.5, abs(v.y) > 150 else { return }
        onChange(v.y < 0)          // finger moving up = content scrolling down = hide
    }
    func gestureRecognizer(_ g: UIGestureRecognizer, shouldRecognizeSimultaneouslyWith other: UIGestureRecognizer) -> Bool { true }
}
#endif


// MARK: - Command Center (iPad + Mac) — laid out like the web Command Center

enum CCScreen: String, CaseIterable, Identifiable {
    case dashboard = "Dashboard", calendar = "Calendar"
    case jobs = "Jobs", estimates = "Estimates", time = "Time Clock", spaces = "Spaces", photos = "Photos", punch = "Punchlist", documents = "Documents", shopping = "Shopping List"
    case dailylog = "Daily Log", eod = "EOD Reports", finance = "Finance", contacts = "Contacts"
    case archive = "Archived Jobs", sync = "Sync Settings", search = "Search"
    var id: String { rawValue }
    var symbol: String {
        switch self {
        case .dashboard: return "square.grid.2x2"
        case .calendar: return "calendar"
        case .jobs: return "briefcase"
        case .estimates: return "doc.text"
        case .time: return "clock"
        case .spaces: return "square.grid.2x2"
        case .photos: return "camera"
        case .punch: return "checkmark.square"
        case .documents: return "doc"
        case .shopping: return "cart"
        case .dailylog: return "list.clipboard"
        case .eod: return "doc.text"
        case .finance: return "dollarsign"
        case .contacts: return "person"
        case .archive: return "archivebox"
        case .sync: return "arrow.triangle.2.circlepath"
        case .search: return "magnifyingglass"
        }
    }
    /// Same highlight colors as the web sidebar.
    var tint: Color {
        switch self {
        case .dashboard, .estimates: return Theme.blue
        case .calendar, .photos, .contacts: return Theme.sky
        case .jobs, .punch, .shopping: return Theme.gold
        case .time, .documents, .finance: return Theme.purple
        case .spaces, .eod, .dailylog: return Theme.orange
        default: return Theme.blue
        }
    }
    static let groups: [(String, [CCScreen])] = [
        ("Overview", [.dashboard, .calendar]),
        ("Field Work", [.jobs, .estimates, .spaces, .photos, .punch, .documents, .shopping]),
        ("Reports", [.dailylog, .eod]),
        ("Finance", [.finance, .time]),
        ("Directory", [.contacts]),
        ("Settings", [.archive, .sync]),
    ]
}

struct CommandCenterView: View {
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @AppStorage("bpZoomPct") private var zoomPct = 100
    @AppStorage("bpCCScreen") private var selRaw = CCScreen.dashboard.rawValue
    private var sel: CCScreen { get { CCScreen(rawValue: selRaw) ?? .dashboard } nonmutating set { selRaw = newValue.rawValue } }
    @AppStorage("bpActiveJob") private var activeKey = ""
    @EnvironmentObject private var shell: ShellState
    @StateObject private var info = HeaderInfo()
    @State private var searchText = ""

    private func key(_ j: Job) -> String { String(j.created.timeIntervalSince1970) }
    private var active: Job? { activeKey.isEmpty ? nil : jobs.first { key($0) == activeKey } }

    var body: some View {
        VStack(spacing: 0) {
            topbar
            Rectangle().fill(Theme.border(dark)).frame(height: 1)
            HStack(spacing: 0) {
                sidebar.frame(width: 240).background(Theme.card(dark))
                Rectangle().fill(Theme.border(dark)).frame(width: 1)
                detail
                    .environmentObject(shell)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Theme.bg(dark))
                    .overlay(alignment: .bottomTrailing) { FloatBar(showBack: false, showMenu: false).environmentObject(shell) }
            }
        }
        .background(Theme.bg(dark).ignoresSafeArea())
        .onAppear { shell.goHome = { sel = .dashboard }; info.start() }
    }

    // MARK: top bar (logo · place / weather / date / time · Sync · Theme · size · New EOD Report)

    private var versionText: String { "v" + ((Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "") }

    private var topbar: some View {
        HStack(spacing: 16) {
            ZStack {
                Circle().stroke(Color.primary, lineWidth: 4.5).frame(width: 96, height: 96)
                Text("B").font(.system(size: 56, weight: .bold, design: .serif))
                Capsule().fill(Color(red: 0.84, green: 0.13, blue: 0.13)).frame(width: 52, height: 7).offset(y: 27)
            }
            VStack(spacing: 4) {
                Text("BuildersPro").font(.system(size: 26, weight: .heavy)).lineLimit(1).fixedSize()
                    .foregroundStyle(LinearGradient(colors: [dark ? Color(white: 0.94) : Color(white: 0.78), Color(white: 0.55)], startPoint: .leading, endPoint: .trailing))
                Text(versionText).font(.system(size: 12, weight: .heavy)).foregroundStyle(Theme.gold)
                    .padding(.horizontal, 10).padding(.vertical, 2)
                    .background(Theme.gold.opacity(0.14), in: Capsule())
                    .overlay(Capsule().stroke(Theme.gold.opacity(0.35)))
            }
            Rectangle().fill(Theme.border(dark)).frame(width: 1, height: 34)
            HStack(spacing: 8) {
                tbButton("arrow.triangle.2.circlepath", "Sync") { sel = .sync }
                tbButton("circle.lefthalf.filled", "Theme") { dark.toggle() }
                Button { shell.sizePop = true } label: {
                    HStack(spacing: 4) {
                        Text("A").font(.system(size: 11, weight: .heavy)); Text("A").font(.system(size: 18, weight: .heavy))
                        Text("\(zoomPct)%").font(.system(size: 15, weight: .bold)).monospacedDigit().padding(.leading, 2)
                    }
                    .lineLimit(1).fixedSize().padding(.horizontal, 16).frame(height: 44)
                    .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border(dark)))
                }.buttonStyle(.plain)
                .popover(isPresented: $shell.sizePop, arrowEdge: .top) { TextSizePanel(showDone: true).frame(width: 440).preferredColorScheme(dark ? .dark : .light) }
                Button { sel = .eod } label: {
                    HStack(spacing: 8) { Image(systemName: "doc.badge.plus").font(.system(size: 19, weight: .bold)); Text("New EOD Report").font(.system(size: 15, weight: .bold)).lineLimit(1) }
                        .fixedSize().padding(.horizontal, 18).frame(height: 44).foregroundStyle(.white)
                        .background(Theme.orange, in: RoundedRectangle(cornerRadius: 10))
                }.buttonStyle(.plain)
            }
            Spacer(minLength: 8)
            ViewThatFits(in: .horizontal) {
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 7) {
                    Image(systemName: "mappin.and.ellipse").foregroundStyle(Theme.blue)
                    Text(info.place).font(.system(size: 19, weight: .bold)).lineLimit(1)
                }
                HStack(spacing: 14) {
                    HStack(spacing: 6) {
                        Image(systemName: info.icon).font(.system(size: 18, weight: .bold)).foregroundStyle(Theme.sky)
                        Text(info.weather).font(.system(size: 15, weight: .medium)).foregroundStyle(Theme.sky).lineLimit(1)
                    }
                    Text(Date.now.formatted(.dateTime.weekday(.abbreviated).month(.twoDigits).day(.twoDigits).year()))
                        .font(.system(size: 14, weight: .medium)).foregroundStyle(Theme.muted(dark)).lineLimit(1)
                }
                TimelineView(.everyMinute) { ctx in
                    Text(ctx.date.formatted(.dateTime.hour().minute()))
                        .font(.system(size: 32, weight: .bold)).foregroundStyle(Theme.blue)
                }
            }
            .fixedSize(horizontal: true, vertical: false)
            Color.clear.frame(width: 1, height: 1)
            }
        }
        .padding(.horizontal, 20).frame(height: 118)
        .background(Theme.card(dark))
    }

    private func tbButton(_ icon: String, _ title: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) { Image(systemName: icon).font(.system(size: 19, weight: .bold)); Text(title).font(.system(size: 14, weight: .bold)).lineLimit(1) }
                .fixedSize().padding(.horizontal, 16).frame(height: 44)
                .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 10))
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border(dark)))
        }.buttonStyle(.plain)
    }

    // MARK: sidebar

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                TextField("SEARCH", text: $searchText)
                    .textFieldStyle(.plain).font(.system(size: 14, weight: .semibold))
                    .padding(.horizontal, 12).frame(height: 40)
                    .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 9))
                    .overlay(RoundedRectangle(cornerRadius: 9).stroke(Theme.border(dark)))
                    .onSubmit { sel = .search }
            }
            .padding(.horizontal, 16).padding(.top, 14).padding(.bottom, 6)
            ScrollView(showsIndicators: false) {
              VStack(alignment: .leading, spacing: 2) {
                ForEach(CCScreen.groups, id: \.0) { g in
                    Text(g.0.uppercased()).font(.system(size: 12, weight: .heavy)).tracking(1.2).foregroundStyle(Theme.faint(dark))
                        .padding(.horizontal, 10).padding(.top, 14).padding(.bottom, 4)
                    ForEach(g.1) { navRow($0) }
                }
              }
              .padding(.horizontal, 8).padding(.bottom, 12)
            }
        }
    }

    private func navRow(_ s: CCScreen) -> some View {
        let on = sel == s
        return Button { sel = s } label: {
            HStack(spacing: 10) {
                Image(systemName: s.symbol).font(.system(size: 20, weight: .bold)).frame(width: 28)
                Text(s.rawValue).font(.system(size: 15, weight: on ? .bold : .semibold))
                Spacer()
            }
            .padding(.horizontal, 14).padding(.vertical, 10).contentShape(Rectangle())
            .foregroundStyle(on ? s.tint : Theme.muted(dark))
            .background(on ? s.tint.opacity(0.15) : .clear, in: RoundedRectangle(cornerRadius: 10))
        }.buttonStyle(.plain)
    }

    // MARK: detail

    @ViewBuilder private var detail: some View {
        switch sel {
        case .dashboard: CCDashboard(open: { sel = $0 })
        case .calendar: AllCalendarView()
        case .jobs: JobsView()
        case .photos: AllPhotosView()
        case .punch: AllPunchView()
        case .finance: AllMoneyView()
        case .search: SearchView(initial: searchText)
        case .spaces: AllSpacesView(startJob: active)
        case .documents: jobScoped("Documents") { DocsView(job: $0) }
        case .eod: jobScoped("EOD Reports") { ReportsView(job: $0) }
        case .dailylog: jobScoped("Daily Log") { ReportsView(job: $0) }
        case .shopping: jobScoped("Shopping List") { ShoppingView(job: $0) }
        case .time: CCTimeClockView()
        case .estimates: CCEstimatesView()
        case .contacts: CCContactsView()
        case .archive: CCArchiveView()
        case .sync: CCSyncView()
        }
    }

    @ViewBuilder private func jobScoped<V: View>(_ title: String, @ViewBuilder _ make: (Job) -> V) -> some View {
        if let j = active {
            NavigationStack {
                make(j).navigationTitle(title)
                    .toolbar { ToolbarItem(placement: .automatic) { jobMenu(label: j.name) } }
            }
        } else {
            VStack(alignment: .leading, spacing: 14) {
                Text(title).font(.system(size: 36, weight: .semibold))
                Text("Pick a job to open it here.").font(.system(size: 15)).foregroundStyle(Theme.muted(dark))
                jobMenu(label: "Select a job")
                Spacer()
            }.padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }

    private func jobMenu(label: String) -> some View {
        Menu {
            ForEach(jobs) { j in Button(j.name) { activeKey = key(j) } }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "mappin.and.ellipse").foregroundStyle(Theme.blue)
                Text(label).font(.system(size: 14, weight: .bold)).foregroundStyle(Theme.blue).lineLimit(1)
                Image(systemName: "chevron.up.chevron.down").font(.caption).foregroundStyle(Theme.muted(dark))
            }
            .padding(.horizontal, 12).frame(height: 38)
            .background(Theme.blue.opacity(0.10), in: RoundedRectangle(cornerRadius: 9))
            .overlay(RoundedRectangle(cornerRadius: 9).stroke(Theme.blue.opacity(0.5)))
        }.menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
    }

    private func soon(_ title: String, _ note: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.system(size: 36, weight: .black))
            Text(note).font(.system(size: 15)).foregroundStyle(Theme.muted(dark))
            Spacer()
        }.padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

// MARK: - Dashboard (same blocks as the web Dashboard)

struct CCDashboard: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @Query private var photos: [SitePhoto]
    @Query(sort: \DailyReport.date, order: .reverse) private var reports: [DailyReport]
    @AppStorage("bpDark") private var dark = true
    let open: (CCScreen) -> Void

    private var activeCount: Int { jobs.filter { $0.status == "Active" }.count }
    private var openItems: Int { jobs.reduce(0) { $0 + ($1.totalCount - $1.doneCount) } }
    private var contractValue: Double { jobs.reduce(0) { $0 + $1.revisedContract } }
    private func money(_ v: Double) -> String { v.formatted(.currency(code: "USD").precision(.fractionLength(0))) }

    /// "Needs your attention" rows — same idea as the web panel.
    private var attention: [(String, String, Color, CCScreen)] {
        var r: [(String, String, Color, CCScreen)] = []
        for j in jobs where j.contract > 0 && j.cashSpent > j.revisedContract {
            r.append(("exclamationmark.triangle.fill", "\(j.name) is \(money(j.cashSpent - j.revisedContract)) over budget", Theme.deskRed, .finance))
        }
        if openItems > 0 { r.append(("checkmark.square", "\(openItems) open punchlist item\(openItems > 1 ? "s" : "")", Theme.orange, .punch)) }
        let unfiled = photos.filter { $0.space == nil }.count
        if unfiled > 0 { r.append(("camera", "\(unfiled) unfiled photo\(unfiled > 1 ? "s" : "")", Theme.sky, .photos)) }
        return r
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Dashboard").font(.system(size: 36, weight: .semibold))
                            Text(Date.now.formatted(.dateTime.weekday(.wide).month(.wide).day().year()))
                                .font(.system(size: 15)).foregroundStyle(Theme.muted(dark))
                        }
                        Spacer()
                        HStack(spacing: 8) {
                            Button { open(.jobs) } label: { pill("+ New Job", fill: Theme.card2(dark), fg: .primary) }.buttonStyle(.plain)
                            Button { open(.eod) } label: { pill("+ EOD Report", fill: Theme.orange, fg: .white) }.buttonStyle(.plain)
                        }
                    }
                    if !attention.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("NEEDS YOUR ATTENTION").font(.system(size: 12, weight: .heavy)).tracking(1).foregroundStyle(Theme.muted(dark))
                            ForEach(attention.indices, id: \.self) { i in
                                let a = attention[i]
                                Button { open(a.3) } label: {
                                    HStack(spacing: 10) {
                                        Image(systemName: a.0).foregroundStyle(a.2)
                                        Text(a.1).font(.system(size: 13, weight: .bold)).foregroundStyle(a.2)
                                        Spacer()
                                    }
                                    .padding(.horizontal, 16).padding(.vertical, 12)
                                    .background(a.2.opacity(0.12), in: RoundedRectangle(cornerRadius: 12))
                                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(a.2.opacity(0.35)))
                                }.buttonStyle(.plain)
                            }
                        }
                    }
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 200), spacing: 14)], spacing: 14) {
                        kpi("\(activeCount)", "Active Jobs", Theme.gold) { open(.jobs) }
                        kpi("\(openItems)", "Open Punchlist Items", Theme.yellow) { open(.punch) }
                        kpi("\(photos.count)", "Total Photos", Theme.sky) { open(.photos) }
                        kpi(money(contractValue), "Contract Value", Theme.blue) { open(.finance) }
                    }
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 340), alignment: .top)], alignment: .leading, spacing: 20) {
                        VStack(alignment: .leading, spacing: 10) {
                            sec("Recent Jobs")
                            if jobs.isEmpty { empty("No jobs yet") }
                            ForEach(Array(jobs.prefix(5))) { j in
                                NavigationLink { JobDetailView(job: j) } label: { jobCard(j) }.buttonStyle(.plain)
                            }
                        }
                        VStack(alignment: .leading, spacing: 10) {
                            sec("Recent EOD Reports")
                            if reports.isEmpty { empty("No reports yet") }
                            ForEach(Array(reports.prefix(5))) { r in
                                Button { open(.eod) } label: { reportCard(r) }.buttonStyle(.plain)
                            }
                        }
                    }
                    Color.clear.frame(height: 90)
                }
                .padding(24)
            }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
        }
    }

    private func pill(_ t: String, fill: Color, fg: Color) -> some View {
        Text(t).font(.system(size: 14, weight: .bold)).foregroundStyle(fg)
            .padding(.horizontal, 16).frame(height: 40)
            .background(fill, in: RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border(dark)))
    }
    private func sec(_ t: String) -> some View {
        Text(t.uppercased()).font(.system(size: 13, weight: .heavy)).tracking(1.2).foregroundStyle(Theme.muted(dark))
    }
    private func empty(_ t: String) -> some View {
        Text(t).foregroundStyle(Theme.muted(dark)).frame(maxWidth: .infinity).padding(.vertical, 24)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
    }
    private func kpi(_ value: String, _ label: String, _ color: Color, tap: @escaping () -> Void) -> some View {
        Button(action: tap) {
            VStack(spacing: 6) {
                Text(value).font(.system(size: 36, weight: .semibold)).foregroundStyle(color).minimumScaleFactor(0.6).lineLimit(1)
                Text(label.uppercased()).font(.system(size: 12, weight: .bold)).tracking(0.8).foregroundStyle(Theme.muted(dark)).lineLimit(1).minimumScaleFactor(0.7)
            }
            .frame(maxWidth: .infinity).padding(.vertical, 22)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
        }.buttonStyle(.plain)
    }
    private func jobCard(_ j: Job) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(j.name).font(.system(size: 14, weight: .bold)).lineLimit(1)
                Spacer()
                Text(j.status).font(.system(size: 12, weight: .bold)).padding(.horizontal, 10).padding(.vertical, 3)
                    .foregroundStyle(j.status == "Active" ? Color.green : Theme.muted(dark))
                    .background((j.status == "Active" ? Color.green : Theme.muted(dark)).opacity(0.15), in: Capsule())
            }
            if !j.client.isEmpty { Text("👤 " + j.client).font(.system(size: 12)).foregroundStyle(Theme.muted(dark)) }
            if j.contract > 0 {
                (Text("Contract \(money(j.contract)) · ").foregroundStyle(Theme.muted(dark))
                 + Text("Balance \(j.remaining < 0 ? "-" : "")\(money(abs(j.remaining)))").foregroundStyle(j.remaining >= 0 ? Theme.blue : Theme.deskRed))
                    .font(.system(size: 12))
            }
            if j.totalCount > 0 {
                GeometryReader { g in
                    ZStack(alignment: .leading) {
                        Capsule().fill(Theme.border(dark))
                        Capsule().fill(Theme.blue).frame(width: g.size.width * CGFloat(j.percent) / 100)
                    }
                }.frame(height: 5).padding(.top, 4)
            }
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
    }
    private func reportCard(_ r: DailyReport) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(r.job?.name ?? "Unknown").font(.system(size: 14, weight: .bold))
                Text(r.date.formatted(.dateTime.month(.abbreviated).day().year())).font(.system(size: 12)).foregroundStyle(Theme.muted(dark))
            }
            Spacer()
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
    }
}


// MARK: - Command Center · Time Clock

struct CCTimeClockView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @Query(sort: \TimeEntry.clockIn, order: .reverse) private var entries: [TimeEntry]
    @AppStorage("bpDark") private var dark = true
    @AppStorage("bpActiveJob") private var activeKey = ""
    @AppStorage("bpWorker") private var worker = ""
    @AppStorage("bpRate") private var rate = ""
    @State private var pickKey = ""

    private func key(_ j: Job) -> String { String(j.created.timeIntervalSince1970) }
    private var pickJob: Job? {
        let k = pickKey.isEmpty ? activeKey : pickKey
        return jobs.first { key($0) == k }
    }
    private var openEntries: [TimeEntry] { entries.filter { $0.isOpen } }
    private var todayHrs: Double { entries.filter { Calendar.current.isDateInToday($0.clockIn) }.reduce(0) { $0 + $1.hours } }
    private var weekHrs: Double { entries.filter { $0.clockIn >= Date().addingTimeInterval(-6 * 86400) }.reduce(0) { $0 + $1.hours } }
    private func hrs(_ v: Double) -> String { (v * 100).rounded() / 100 == v.rounded() ? "\(Int(v.rounded()))" : String(format: "%.2f", v) }
    private func usd(_ v: Double) -> String { v.formatted(.currency(code: "USD").precision(.fractionLength(2))) }
    private func hm(_ d: Date) -> String { d.formatted(.dateTime.hour().minute()) }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Time Clock").font(.system(size: 36, weight: .semibold)).foregroundStyle(Theme.purple)
                        Text("\(entries.count) entr\(entries.count == 1 ? "y" : "ies")").font(.system(size: 15)).foregroundStyle(Theme.muted(dark))
                    }
                    clockCard
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 220), spacing: 14)], spacing: 14) {
                        kpi("\(hrs(todayHrs)) hrs", "Today", Theme.blue)
                        kpi("\(hrs(weekHrs)) hrs", "Last 7 Days", Theme.sky)
                    }
                    Text("LOG").font(.system(size: 13, weight: .heavy)).tracking(1.2).foregroundStyle(Theme.muted(dark))
                    if entries.isEmpty {
                        Text("No time logged yet").foregroundStyle(Theme.muted(dark)).frame(maxWidth: .infinity).padding(.vertical, 28)
                            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
                    } else {
                        VStack(spacing: 0) {
                            headerRow
                            ForEach(entries) { e in Divider(); row(e) }
                        }
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
                    }
                    Color.clear.frame(height: 90)
                }
                .padding(24)
            }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
        }
    }

    private var clockCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(openEntries) { e in
                HStack(spacing: 12) {
                    Image(systemName: "clock.badge.checkmark").font(.title2).foregroundStyle(.green)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Clocked in · \(e.job?.name ?? "Unknown job")").font(.system(size: 16, weight: .bold))
                        Text("since \(hm(e.clockIn)) · \(hrs(e.hours)) hrs").font(.system(size: 13)).foregroundStyle(Theme.muted(dark))
                    }
                    Spacer()
                    Button { e.clockOut = Date(); e.isOpen = false } label: {
                        Text("Clock Out").font(.system(size: 14, weight: .bold)).foregroundStyle(.white)
                            .padding(.horizontal, 18).frame(height: 40).background(Theme.deskRed, in: RoundedRectangle(cornerRadius: 10))
                    }.buttonStyle(.plain)
                }
                Divider()
            }
            HStack(spacing: 10) {
                Menu {
                    ForEach(jobs) { j in Button(j.name) { pickKey = key(j) } }
                } label: {
                    HStack { Text(pickJob?.name ?? "Pick a job").lineLimit(1); Spacer(); Image(systemName: "chevron.up.chevron.down").font(.caption) }
                        .font(.system(size: 14, weight: .semibold)).foregroundStyle(pickJob == nil ? Theme.muted(dark) : Color.primary)
                        .padding(.horizontal, 12).frame(height: 40).frame(minWidth: 220)
                        .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 9))
                        .overlay(RoundedRectangle(cornerRadius: 9).stroke(Theme.border(dark)))
                }.menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                field("Your name", $worker, 160)
                field("$ / hr", $rate, 90)
                Spacer()
                Button { clockIn() } label: {
                    Text("Clock In").font(.system(size: 14, weight: .bold)).foregroundStyle(.white)
                        .padding(.horizontal, 22).frame(height: 40)
                        .background(pickJob == nil ? Theme.muted(dark) : Theme.blue, in: RoundedRectangle(cornerRadius: 10))
                }.buttonStyle(.plain).disabled(pickJob == nil)
            }
        }
        .padding(18)
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
    }

    private func field(_ ph: String, _ text: Binding<String>, _ w: CGFloat) -> some View {
        TextField(ph, text: text).textFieldStyle(.plain).font(.system(size: 14, weight: .semibold))
            .padding(.horizontal, 12).frame(width: w, height: 40)
            .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 9))
            .overlay(RoundedRectangle(cornerRadius: 9).stroke(Theme.border(dark)))
    }

    private func clockIn() {
        guard let j = pickJob else { return }
        let e = TimeEntry(worker: worker)
        e.clockIn = Date(); e.clockOut = Date(); e.isOpen = true
        e.rate = Double(rate.replacingOccurrences(of: "$", with: "")) ?? 0
        e.job = j
        context.insert(e)
    }

    private func kpi(_ value: String, _ label: String, _ color: Color) -> some View {
        VStack(spacing: 6) {
            Text(value).font(.system(size: 36, weight: .semibold)).foregroundStyle(color)
            Text(label.uppercased()).font(.system(size: 12, weight: .bold)).tracking(0.8).foregroundStyle(Theme.muted(dark))
        }
        .frame(maxWidth: .infinity).padding(.vertical, 22)
        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
    }

    private var headerRow: some View {
        HStack(spacing: 8) {
            ForEach([("JOB", 3.0), ("DATE", 1.4), ("CLOCK IN → OUT", 2.2), ("BY", 1.4), ("HOURS", 1.0), ("$", 1.2)], id: \.0) { h in
                Text(h.0).font(.system(size: 12, weight: .heavy)).tracking(0.8).foregroundStyle(Theme.muted(dark)).frame(maxWidth: .infinity, alignment: .leading).layoutPriority(h.1)
            }
            Spacer().frame(width: 34)
        }.padding(.horizontal, 16).padding(.vertical, 12)
    }

    private func row(_ e: TimeEntry) -> some View {
        HStack(spacing: 8) {
            Text(e.job?.name ?? "Unknown job").font(.system(size: 14, weight: .bold)).lineLimit(1).frame(maxWidth: .infinity, alignment: .leading).layoutPriority(3)
            Text(e.clockIn.formatted(.dateTime.month(.twoDigits).day(.twoDigits).year())).font(.system(size: 13)).frame(maxWidth: .infinity, alignment: .leading).layoutPriority(1.4)
            Text("\(hm(e.clockIn)) → \(e.isOpen ? "in progress" : hm(e.clockOut))").font(.system(size: 12)).foregroundStyle(Theme.muted(dark)).frame(maxWidth: .infinity, alignment: .leading).layoutPriority(2.2)
            Text(e.worker.isEmpty ? "—" : e.worker).font(.system(size: 12)).foregroundStyle(Theme.muted(dark)).frame(maxWidth: .infinity, alignment: .leading).layoutPriority(1.4)
            Text(hrs(e.hours)).font(.system(size: 14, weight: .bold)).frame(maxWidth: .infinity, alignment: .leading).layoutPriority(1)
            Text(e.rate > 0 ? usd(e.hours * e.rate) : "—").font(.system(size: 13)).frame(maxWidth: .infinity, alignment: .leading).layoutPriority(1.2)
            Button { context.delete(e) } label: { Image(systemName: "trash").foregroundStyle(Theme.deskRed).frame(width: 34, height: 30) }.buttonStyle(.plain)
        }.padding(.horizontal, 16).padding(.vertical, 12)
    }
}


// MARK: - Command Center · Estimates

struct CCEstimatesView: View {
    @Query(sort: \Estimate.created, order: .reverse) private var estimates: [Estimate]
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    @State private var sheet: EstimateRequest?
    @State private var openJob: Job?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Estimates").font(.system(size: 36, weight: .semibold)).foregroundStyle(Theme.blue)
                            Text("\(estimates.count) estimate\(estimates.count == 1 ? "" : "s")").font(.system(size: 15)).foregroundStyle(Theme.muted(dark))
                        }
                        Spacer()
                        Button { sheet = EstimateRequest(est: nil) } label: {
                            Text("+ New Estimate").font(.system(size: 14, weight: .bold)).foregroundStyle(.white)
                                .padding(.horizontal, 18).frame(height: 40).background(Theme.blue, in: RoundedRectangle(cornerRadius: 10))
                        }.buttonStyle(.plain)
                    }
                    if estimates.isEmpty {
                        Text("No estimates yet").foregroundStyle(Theme.muted(dark)).frame(maxWidth: .infinity).padding(.vertical, 40)
                            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
                    } else {
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 380), spacing: 14, alignment: .top)], alignment: .leading, spacing: 14) {
                            ForEach(estimates) { e in
                                EstimateCard(est: e, edit: { sheet = EstimateRequest(est: e) }, open: { key in
                                    if let j = jobs.first(where: { String($0.created.timeIntervalSince1970) == key }) { openJob = j }
                                })
                            }
                        }
                    }
                    Color.clear.frame(height: 90)
                }
                .padding(24)
            }
            .sheet(item: $sheet) { EstimateSheet(est: $0.est) }
            .navigationDestination(item: $openJob) { JobDetailView(job: $0) }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
        }
    }
}


// MARK: - Command Center · shared page pieces

private struct CCPage<Content: View>: View {
    let title: String, sub: String, tint: Color?
    @ViewBuilder let content: Content
    @AppStorage("bpDark") private var dark = true
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(title).font(.system(size: 36, weight: .semibold)).foregroundStyle(tint ?? Color.primary)
                        if !sub.isEmpty { Text(sub).font(.system(size: 15)).foregroundStyle(Theme.muted(dark)) }
                    }
                    content
                    Color.clear.frame(height: 90)
                }
                .padding(24).frame(maxWidth: .infinity, alignment: .leading)
            }
            #if os(iOS)
            .toolbar(.hidden, for: .navigationBar)
            #endif
        }
    }
}

// MARK: - Command Center · Contacts (owners · clients · contractors · suppliers, built from your jobs)

struct CCContactsView: View {
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @Query(sort: \Vendor.name) private var vendors: [Vendor]
    @AppStorage("bpDark") private var dark = true
    @State private var filter = "All Types"

    struct Contact: Identifiable {
        let id = UUID()
        let name: String, type: String, detail: String, phone: String, email: String, job: String
    }

    private var contacts: [Contact] {
        var out: [Contact] = []
        var seen = Set<String>()
        for j in jobs {
            let c = j.client.trimmingCharacters(in: .whitespaces)
            if !c.isEmpty, seen.insert("c|" + c.lowercased()).inserted {
                out.append(Contact(name: c, type: "Client", detail: j.address, phone: j.clientPhone, email: j.clientEmail, job: j.name))
            }
            for k in j.contractors ?? [] where !k.name.isEmpty {
                out.append(Contact(name: k.name, type: "Contractor", detail: k.trade, phone: k.phone, email: "", job: j.name))
            }
        }
        for v in vendors where !v.name.isEmpty { out.append(Contact(name: v.name, type: "Supplier", detail: "", phone: "", email: "", job: "")) }
        return out.sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
    }
    private var shown: [Contact] { filter == "All Types" ? contacts : contacts.filter { $0.type == filter.dropLast() } }
    private func tint(_ t: String) -> Color { t == "Client" ? Theme.sky : t == "Contractor" ? Theme.gold : Theme.purple }

    var body: some View {
        CCPage(title: "Contacts", sub: "Owners · Clients · Contractors", tint: Theme.sky) {
            HStack {
                Menu {
                    ForEach(["All Types", "Clients", "Contractors", "Suppliers"], id: \.self) { t in Button(t) { filter = t } }
                } label: {
                    HStack { Text(filter); Image(systemName: "chevron.up.chevron.down").font(.caption) }
                        .font(.system(size: 14, weight: .semibold)).padding(.horizontal, 14).frame(height: 40)
                        .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 9))
                        .overlay(RoundedRectangle(cornerRadius: 9).stroke(Theme.border(dark)))
                }.menuStyle(.button).menuIndicator(.hidden).buttonStyle(.plain)
                Spacer()
                Text("\(shown.count) contact\(shown.count == 1 ? "" : "s")").font(.system(size: 14)).foregroundStyle(Theme.muted(dark))
            }
            if shown.isEmpty {
                Text("No contacts yet").foregroundStyle(Theme.muted(dark)).frame(maxWidth: .infinity).padding(.vertical, 40)
                    .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
            } else {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 300), spacing: 14, alignment: .top)], alignment: .leading, spacing: 14) {
                    ForEach(shown) { c in
                        VStack(alignment: .leading, spacing: 5) {
                            HStack {
                                Text(c.name).font(.system(size: 16, weight: .bold)).lineLimit(1)
                                Spacer()
                                Text(c.type).font(.system(size: 12, weight: .bold)).foregroundStyle(tint(c.type))
                                    .padding(.horizontal, 10).padding(.vertical, 3).background(tint(c.type).opacity(0.15), in: Capsule())
                            }
                            if !c.detail.isEmpty { Text(c.detail).font(.system(size: 13)).foregroundStyle(Theme.muted(dark)) }
                            if !c.phone.isEmpty { Label(c.phone, systemImage: "phone").font(.system(size: 13)) }
                            if !c.email.isEmpty { Label(c.email, systemImage: "envelope").font(.system(size: 13)) }
                            if !c.job.isEmpty { Text(c.job).font(.system(size: 12, weight: .semibold)).foregroundStyle(Theme.muted(dark)) }
                        }
                        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
                        .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
                    }
                }
            }
        }
    }
}

// MARK: - Command Center · Archived Jobs

struct CCArchiveView: View {
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpDark") private var dark = true
    private var archived: [Job] { jobs.filter { $0.status == "Archived" } }
    private var finished: [Job] { jobs.filter { $0.status == "Complete" } }

    var body: some View {
        CCPage(title: "Archived Jobs", sub: "Completed jobs moved out of the active lists", tint: nil) {
            section("Ready to archive", finished, "Archive") { $0.status = "Archived"; $0.isActive = false }
            section("Archived", archived, "Restore") { $0.status = "Complete" }
        }
    }

    @ViewBuilder private func section(_ title: String, _ list: [Job], _ action: String, _ run: @escaping (Job) -> Void) -> some View {
        Text(title.uppercased()).font(.system(size: 13, weight: .heavy)).tracking(1.2).foregroundStyle(Theme.muted(dark))
        if list.isEmpty {
            Text(title == "Archived" ? "Nothing archived yet" : "No completed jobs").foregroundStyle(Theme.muted(dark)).frame(maxWidth: .infinity).padding(.vertical, 28)
                .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
        } else {
            ForEach(list) { j in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(j.name).font(.system(size: 15, weight: .bold))
                        Text([j.client, j.address].filter { !$0.isEmpty }.joined(separator: " · ")).font(.system(size: 12)).foregroundStyle(Theme.muted(dark))
                    }
                    Spacer()
                    Button { run(j) } label: {
                        Text(action).font(.system(size: 13, weight: .bold)).padding(.horizontal, 16).frame(height: 36)
                            .background(Theme.card2(dark), in: RoundedRectangle(cornerRadius: 9))
                            .overlay(RoundedRectangle(cornerRadius: 9).stroke(Theme.border(dark)))
                    }.buttonStyle(.plain)
                }
                .padding(16).background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
            }
        }
    }
}

// MARK: - Command Center · Sync Settings (iCloud)

struct CCSyncView: View {
    @Query private var jobs: [Job]
    @Query private var photos: [SitePhoto]
    @Query private var items: [PunchItem]
    @AppStorage("bpDark") private var dark = true
    private var signedIn: Bool { FileManager.default.ubiquityIdentityToken != nil }

    var body: some View {
        CCPage(title: "Sync Settings", sub: "Your data syncs through iCloud — no setup, no tokens", tint: nil) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 12) {
                    Image(systemName: signedIn ? "checkmark.icloud.fill" : "exclamationmark.icloud.fill").font(.title).foregroundStyle(signedIn ? Color.green : Theme.orange)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(signedIn ? "iCloud is on" : "Not signed in to iCloud").font(.system(size: 17, weight: .bold))
                        Text(signedIn ? "Jobs, photos and checklists sync to every device signed in to your Apple ID."
                                      : "Sign in to iCloud in System Settings to sync with your iPhone and iPad.")
                            .font(.system(size: 13)).foregroundStyle(Theme.muted(dark))
                    }
                }
                Divider()
                HStack(spacing: 28) {
                    stat("\(jobs.count)", "Jobs"); stat("\(items.count)", "Checklist items"); stat("\(photos.count)", "Photos")
                    Spacer()
                }
            }
            .padding(18).frame(maxWidth: 560, alignment: .leading)
            .background(Theme.card(dark), in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.border(dark)))
        }
    }

    private func stat(_ v: String, _ l: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(v).font(.system(size: 26, weight: .semibold)).foregroundStyle(Theme.blue)
            Text(l.uppercased()).font(.system(size: 11, weight: .bold)).tracking(0.8).foregroundStyle(Theme.muted(dark))
        }
    }
}


// MARK: - Text & button size panel (same control as the web apps: 85–180%, A− / A+, six presets)

struct TextSizePanel: View {
    @AppStorage("bpZoomPct") private var pct = 100
    @AppStorage("bpDark") private var dark = true
    @Environment(\.dismiss) private var dismiss
    var showDone = true
    private let presets: [(Int, String)] = [(100, "Normal"), (115, "Large"), (130, "XL"), (145, "XXL"), (160, "Jumbo"), (180, "Max")]

    private func clamp(_ v: Int) -> Int { min(180, max(85, Int((Double(v) / 5).rounded()) * 5)) }

    var body: some View {
        VStack(spacing: 18) {
            HStack {
                Text("Drag and watch the app change").font(.system(size: 13, weight: .bold)).foregroundStyle(.secondary)
                Spacer()
                if showDone {
                    Button { dismiss() } label: {
                        Text("Done").font(.system(size: 16, weight: .heavy)).foregroundStyle(.white)
                            .padding(.horizontal, 26).frame(height: 40).background(Theme.blue, in: Capsule())
                    }.buttonStyle(.plain)
                }
            }
            VStack(spacing: 16) {
                HStack(alignment: .firstTextBaseline) {
                    Text("Text & button size").font(.system(size: 15, weight: .bold)).foregroundStyle(.secondary)
                    Spacer()
                    Text("\(pct)").font(.system(size: 40, weight: .heavy)) + Text("%").font(.system(size: 20, weight: .heavy)).foregroundColor(.secondary)
                }
                HStack(spacing: 12) {
                    stepButton("A−") { pct = clamp(pct - 5) }
                    Slider(value: Binding(get: { Double(pct) }, set: { pct = clamp(Int($0)) }), in: 85...180, step: 5)
                    stepButton("A+") { pct = clamp(pct + 5) }
                }
                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 3), spacing: 10) {
                    ForEach(presets, id: \.0) { p in
                        let on = pct == p.0
                        Button { pct = p.0 } label: {
                            VStack(spacing: 2) {
                                Text(p.1).font(.system(size: 16, weight: .heavy))
                                Text("\(p.0)%").font(.system(size: 12, weight: .bold)).opacity(0.7)
                            }
                            .frame(maxWidth: .infinity, minHeight: 56)
                            .foregroundStyle(on ? Color.white : Color.primary)
                            .background(on ? AnyShapeStyle(Theme.blue) : AnyShapeStyle(.thinMaterial), in: RoundedRectangle(cornerRadius: 16))
                            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.white.opacity(on ? 0 : 0.35)))
                        }.buttonStyle(.plain)
                    }
                }
            }
            .padding(18)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 22))
            .overlay(RoundedRectangle(cornerRadius: 22).stroke(Color.white.opacity(0.4)))
        }
        .padding(18)
    }

    private func stepButton(_ t: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(t).font(.system(size: 18, weight: .heavy)).frame(width: 52, height: 52)
                .background(.thinMaterial, in: Circle()).overlay(Circle().stroke(Color.white.opacity(0.4)))
        }.buttonStyle(.plain)
    }
}
