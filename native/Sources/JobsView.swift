import SwiftUI
import SwiftData
import UniformTypeIdentifiers

struct JobsView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @State private var newName = ""
    @State private var adding = false
    @State private var picking = false
    @State private var importing = false
    @State private var report = ""
    @State private var showReport = false

    var body: some View {
        NavigationStack {
            List {
                ForEach(jobs) { job in
                    NavigationLink(value: job) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(job.name).font(.headline).lineLimit(1)      // names never wrap
                            HStack {
                                ProgressView(value: Double(job.percent), total: 100)
                                Text("\(job.percent)%").font(.caption.bold())
                            }
                            Text("\(job.doneCount)/\(job.totalCount) done" +
                                 (job.totalCount > job.doneCount ? " · \(job.totalCount - job.doneCount) left" : ""))
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(jobs[$0]) } }
            }
            .navigationTitle("Jobs")
            .navigationDestination(for: Job.self) { JobDetailView(job: $0) }
            .toolbar {
                // one button holds the options (standing rule)
                Menu {
                    Button("Add a job", systemImage: "plus") { adding = true }
                    Button("Import backup file…", systemImage: "square.and.arrow.down") { picking = true }
                } label: { Image(systemName: "line.3.horizontal") }
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
            .alert("Import", isPresented: $showReport) {
                Button("OK", role: .cancel) {}
            } message: { Text(report) }
            .overlay { if jobs.isEmpty && !importing { ContentUnavailableView("No jobs yet", systemImage: "hammer", description: Text("Use the ≡ button to add a job or import your backup.")) } }
            .overlay { if importing { ProgressView("Importing your jobs…").padding(24).background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14)) } }
        }
    }

    private func runImport(_ url: URL) {
        importing = true
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 300_000_000)      // let the spinner draw first
            do { report = try BackupImporter.run(url: url, context: context).text }
            catch { report = "Could not import: \(error.localizedDescription)" }
            importing = false
            showReport = true
        }
    }
}

// MARK: - Import from the web app's "Full backup" file (BuildersPro-….json)

enum BackupImporter {
    struct Summary {
        var jobs = 0, spaces = 0, punch = 0, photos = 0
        var expenses = 0, contractors = 0, payments = 0, reports = 0
        var text: String {
            var parts: [String] = []
            if jobs > 0 { parts.append("\(jobs) new job(s): \(spaces) spaces, \(punch) punch items, \(photos) photos") }
            if expenses + contractors + payments + reports > 0 {
                parts.append("\(expenses) expenses, \(contractors) contractors, \(payments) payments, \(reports) daily reports")
            }
            return parts.isEmpty ? "Nothing new to import. Everything in that file is already here."
                                 : "Imported " + parts.joined(separator: "; ") + "."
        }
    }

    enum Failure: LocalizedError {
        case notBackup
        var errorDescription: String? { "That file is not a BuildersPro backup." }
    }

    private static let isoFraction: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]; return f
    }()
    private static let isoPlain = ISO8601DateFormatter()
    private static let dayOnly: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.dateFormat = "yyyy-MM-dd"; return f
    }()

    private static func date(_ value: Any?) -> Date? {
        guard let s = value as? String, !s.isEmpty else { return nil }
        return isoFraction.date(from: s) ?? isoPlain.date(from: s) ?? dayOnly.date(from: s)
    }

    private static func num(_ value: Any?) -> Double { (value as? NSNumber)?.doubleValue ?? Double((value as? String) ?? "") ?? 0 }

    private static func str(_ value: Any?) -> String {
        if let s = value as? String { return s }
        if let n = value as? NSNumber { return n.stringValue }
        return ""
    }

    /// Same guess the web app makes for old rooms that never got a level.
    private static func level(of r: [String: Any]) -> String {
        if let l = r["level"] as? String, !l.isEmpty { return l }
        let name = (r["name"] as? String) ?? ""
        let type = (r["type"] as? String) ?? ""
        let space = (r["space"] as? String) ?? ""
        let roof = #"\b(roof|gutter|downspout|leader|chimney|skylight|shingle)"#
        let base = #"\b(basement|cellar|boiler|sump)\b"#
        if type == "Roof" || name.range(of: roof, options: [.regularExpression, .caseInsensitive]) != nil { return "Roof" }
        if space == "Exterior" { return "Outside" }
        if type == "Basement" || name.range(of: base, options: [.regularExpression, .caseInsensitive]) != nil { return "Basement" }
        return ""
    }

    private static func photoData(_ src: Any?) -> Data? {
        guard let s = src as? String, let r = s.range(of: "base64,") else { return nil }
        return Data(base64Encoded: String(s[r.upperBound...]), options: .ignoreUnknownCharacters)
    }

    static func run(url: URL, context: ModelContext) throws -> Summary {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }

        let data = try Data(contentsOf: url, options: .mappedIfSafe)
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let db = root["db"] as? [String: Any] else { throw Failure.notBackup }

        let jobList = db["jobs"] as? [[String: Any]] ?? []
        let rooms = db["rooms"] as? [[String: Any]] ?? []
        let punch = db["punchlist"] as? [[String: Any]] ?? []
        let photos = db["photos"] as? [[String: Any]] ?? []
        let expenseList = db["expenses"] as? [[String: Any]] ?? []
        let contractorList = db["contractors"] as? [[String: Any]] ?? []
        let paymentList = db["payments"] as? [[String: Any]] ?? []
        let reportList = db["reports"] as? [[String: Any]] ?? []

        // What is already here, so importing the same file twice never duplicates anything.
        var jobBySource: [String: Job] = [:]
        for j in (try? context.fetch(FetchDescriptor<Job>())) ?? [] where !j.sourceID.isEmpty { jobBySource[j.sourceID] = j }
        let haveExpense = Set(((try? context.fetch(FetchDescriptor<Expense>())) ?? []).map { $0.sourceID })
        let haveContractor = Set(((try? context.fetch(FetchDescriptor<Contractor>())) ?? []).map { $0.sourceID })
        let haveReport = Set(((try? context.fetch(FetchDescriptor<DailyReport>())) ?? []).map { $0.sourceID })

        var out = Summary()
        for j in jobList {
            let jid = (j["id"] as? String) ?? ""
            if jid.isEmpty { continue }

            // Find the job, or create it (with its spaces, punch items and photos) the first time.
            let job: Job
            if let existing = jobBySource[jid] {
                job = existing
                if job.contract == 0 { job.contract = num(j["contract"]) }
            } else {
                job = Job(name: (j["name"] as? String) ?? "Untitled job")
                job.sourceID = jid
                job.client = (j["client"] as? String) ?? ""
                let stateZip = [(j["state"] as? String) ?? "", (j["zip"] as? String) ?? ""].filter { !$0.isEmpty }.joined(separator: " ")
                job.address = [(j["address"] as? String) ?? "", (j["city"] as? String) ?? "", stateZip].filter { !$0.isEmpty }.joined(separator: ", ")
                job.isActive = ((j["status"] as? String) ?? "") != "Complete"
                job.created = date(j["created"]) ?? date(j["startDate"]) ?? Date()
                job.contract = num(j["contract"])
                context.insert(job)
                jobBySource[jid] = job
                out.jobs += 1

                // Spaces (the web app calls them rooms)
                var spaceByRoom: [String: Space] = [:]
                let myRooms = rooms.filter { ($0["jobId"] as? String) == jid }
                for (i, r) in myRooms.enumerated() {
                    let arranged = (r["order"] as? NSNumber)?.intValue
                    let s = Space(name: (r["name"] as? String) ?? "Space",
                                  level: level(of: r),
                                  order: arranged ?? (1000 + i),
                                  isExterior: ((r["space"] as? String) ?? "") == "Exterior")
                    context.insert(s)
                    s.job = job
                    if let rid = r["id"] as? String { spaceByRoom[rid] = s }
                    out.spaces += 1
                }

                // Punch items (no matching space = General)
                for p in punch where (p["jobId"] as? String) == jid {
                    let item = PunchItem(text: (p["text"] as? String) ?? "", trade: (p["trade"] as? String) ?? "")
                    item.done = (p["done"] as? Bool) ?? false
                    item.created = date(p["created"]) ?? Date()
                    if item.done { item.completed = date(p["completedAt"]) ?? item.created }
                    context.insert(item)
                    item.job = job
                    if let rid = p["roomId"] as? String { item.space = spaceByRoom[rid] }
                    out.punch += 1
                }

                // Photos taken in spaces
                for ph in photos where (ph["jobId"] as? String) == jid {
                    guard let bytes = photoData(ph["src"]) else { continue }
                    let pic = SitePhoto(data: bytes)
                    pic.caption = (ph["caption"] as? String) ?? ""
                    pic.created = date(ph["date"]) ?? Date()
                    context.insert(pic)
                    pic.job = job
                    if let rid = ph["roomId"] as? String { pic.space = spaceByRoom[rid] }
                    out.photos += 1
                }
            }

            // Money — added to the job whether it is new or was imported earlier.
            for e in expenseList where (e["jobId"] as? String) == jid {
                let sid = (e["id"] as? String) ?? ""
                if sid.isEmpty || haveExpense.contains(sid) { continue }
                let x = Expense(title: str(e["desc"]), amount: num(e["amount"]))
                x.sourceID = sid
                x.vendor = str(e["vendor"])
                x.category = str(e["category"])
                x.date = date(e["date"]) ?? date(e["created"]) ?? Date()
                if let items = e["items"] as? [[String: Any]] {
                    x.itemsText = items.map { item in
                        let name = str(item["name"]).isEmpty ? "Item" : str(item["name"])
                        return name + " — " + String(format: "%.2f", num(item["cost"]))
                    }.joined(separator: "\n")
                }
                x.receipt = photoData(e["receiptSrc"])
                context.insert(x)
                x.job = job
                out.expenses += 1
            }

            var contractorBySource: [String: Contractor] = [:]
            for c in contractorList where (c["jobId"] as? String) == jid {
                let sid = (c["id"] as? String) ?? ""
                if sid.isEmpty || haveContractor.contains(sid) { continue }
                let k = Contractor(name: str(c["name"]).isEmpty ? "Contractor" : str(c["name"]))
                k.sourceID = sid
                k.trade = str(c["trade"])
                k.value = num(c["value"])
                k.scope = str(c["scope"])
                k.phone = str(c["phone"])
                k.status = str(c["status"]).isEmpty ? "Active" : str(c["status"])
                context.insert(k)
                k.job = job
                contractorBySource[sid] = k
                out.contractors += 1
            }
            for p in paymentList {
                guard let cid = p["contractorId"] as? String, let k = contractorBySource[cid] else { continue }
                let pay = Payment(amount: num(p["amount"]))
                pay.date = date(p["date"]) ?? date(p["created"]) ?? Date()
                pay.method = str(p["method"]).isEmpty ? "Other" : str(p["method"])
                pay.notes = str(p["notes"])
                context.insert(pay)
                pay.contractor = k
                out.payments += 1
            }

            for r in reportList where (r["jobId"] as? String) == jid {
                let sid = (r["id"] as? String) ?? ""
                if sid.isEmpty || haveReport.contains(sid) { continue }
                let rep = DailyReport(number: str(r["dprNumber"]))
                rep.sourceID = sid
                rep.date = date(r["date"]) ?? date(r["createdAt"]) ?? Date()
                rep.workers = Int(num(r["workers"]))
                rep.hours = str(r["hours"])
                rep.weather = str(r["weather"])
                rep.completed = str(r["completed"])
                rep.incomplete = str(r["incomplete"])
                rep.tomorrow = str(r["tomorrow"])
                rep.visitors = str(r["visitors"])
                rep.safety = str(r["safety"])
                rep.clientNotes = str(r["clientNotes"])
                rep.progress = Int(num(r["progress"]))
                context.insert(rep)
                rep.job = job
                out.reports += 1
            }
            try context.save()
        }
        return out
    }
}
