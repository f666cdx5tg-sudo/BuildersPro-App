import SwiftUI
import SwiftData
import UniformTypeIdentifiers

// MARK: - Import from the web app's "Full backup" file (BuildersPro-….json)

enum BackupImporter {
    struct Summary {
        var jobs = 0, spaces = 0, punch = 0, photos = 0
        var expenses = 0, contractors = 0, payments = 0, reports = 0
        var changeOrders = 0, invoices = 0, permits = 0, timeEntries = 0
        var appointments = 0, shopping = 0, vendors = 0, documents = 0, punchPhotos = 0
        var text: String {
            var parts: [String] = []
            if jobs > 0 { parts.append("\(jobs) new job(s): \(spaces) spaces, \(punch) punch items, \(photos) photos") }
            if expenses + contractors + payments + reports > 0 {
                parts.append("\(expenses) expenses, \(contractors) contractors, \(payments) payments, \(reports) daily reports")
            }
            if changeOrders + invoices + permits + timeEntries > 0 {
                parts.append("\(changeOrders) change orders, \(invoices) invoices, \(permits) permits, \(timeEntries) time entries")
            }
            if appointments + shopping + vendors + documents > 0 {
                parts.append("\(appointments) appointments, \(shopping) shopping items, \(vendors) vendors, \(documents) documents")
            }
            if punchPhotos > 0 { parts.append("\(punchPhotos) punch-item photos") }
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

    private static func fillExtras(_ job: Job, _ j: [String: Any]) {
        if job.clientEmail.isEmpty { job.clientEmail = str(j["clientEmail"]) }
        if job.clientPhone.isEmpty { job.clientPhone = str(j["clientPhone"]) }
        let st = str(j["status"]); if !st.isEmpty { job.status = st }
        if job.startDate == nil { job.startDate = date(j["startDate"]) }
        if job.completionDate == nil { job.completionDate = date(j["completionDate"]) }
        if job.jobNotes.isEmpty { job.jobNotes = str(j["notes"]) }
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
        let changeOrderList = db["changeOrders"] as? [[String: Any]] ?? []
        let invoiceList = db["invoices"] as? [[String: Any]] ?? []
        let permitList = db["permits"] as? [[String: Any]] ?? []
        let timeList = db["timeEntries"] as? [[String: Any]] ?? []
        let apptList = db["appointments"] as? [[String: Any]] ?? []
        let shopList = db["shopping"] as? [[String: Any]] ?? []
        let vendorList = db["vendors"] as? [[String: Any]] ?? []
        let docList = db["documents"] as? [[String: Any]] ?? []

        var out = Summary()

        // What is already here, so importing the same file twice never duplicates anything.
        var jobBySource: [String: Job] = [:]
        for j in (try? context.fetch(FetchDescriptor<Job>())) ?? [] where !j.sourceID.isEmpty { jobBySource[j.sourceID] = j }
        let haveExpense = Set(((try? context.fetch(FetchDescriptor<Expense>())) ?? []).map { $0.sourceID })
        let haveContractor = Set(((try? context.fetch(FetchDescriptor<Contractor>())) ?? []).map { $0.sourceID })
        let haveReport = Set(((try? context.fetch(FetchDescriptor<DailyReport>())) ?? []).map { $0.sourceID })
        let haveCO = Set(((try? context.fetch(FetchDescriptor<ChangeOrder>())) ?? []).map { $0.sourceID })
        let haveInvoice = Set(((try? context.fetch(FetchDescriptor<Invoice>())) ?? []).map { $0.sourceID })
        let havePermit = Set(((try? context.fetch(FetchDescriptor<Permit>())) ?? []).map { $0.sourceID })
        let haveTime = Set(((try? context.fetch(FetchDescriptor<TimeEntry>())) ?? []).map { $0.sourceID })
        let haveAppt = Set(((try? context.fetch(FetchDescriptor<Appointment>())) ?? []).map { $0.sourceID })
        let haveShop = Set(((try? context.fetch(FetchDescriptor<ShoppingItem>())) ?? []).map { $0.sourceID })
        let haveDoc = Set(((try? context.fetch(FetchDescriptor<JobDocument>())) ?? []).map { $0.sourceID })
        var vendorNames = Set(((try? context.fetch(FetchDescriptor<Vendor>())) ?? []).map { $0.name.lowercased() })

        // Vendors are shared across jobs; the web list has repeats, so keep one of each name.
        for v in vendorList {
            let name = str(v["name"]).trimmingCharacters(in: .whitespaces)
            if name.isEmpty || vendorNames.contains(name.lowercased()) { continue }
            vendorNames.insert(name.lowercased())
            let vv = Vendor(name: name); vv.sourceID = str(v["id"])
            context.insert(vv)
            out.vendors += 1
        }

        for j in jobList {
            let jid = (j["id"] as? String) ?? ""
            if jid.isEmpty { continue }

            // Find the job, or create it (with its spaces, punch items and photos) the first time.
            let job: Job
            if let existing = jobBySource[jid] {
                job = existing
                if job.contract == 0 { job.contract = num(j["contract"]) }
                fillExtras(job, j)
            } else {
                job = Job(name: (j["name"] as? String) ?? "Untitled job")
                job.sourceID = jid
                job.client = (j["client"] as? String) ?? ""
                let stateZip = [(j["state"] as? String) ?? "", (j["zip"] as? String) ?? ""].filter { !$0.isEmpty }.joined(separator: " ")
                job.address = [(j["address"] as? String) ?? "", (j["city"] as? String) ?? "", stateZip].filter { !$0.isEmpty }.joined(separator: ", ")
                job.isActive = ((j["status"] as? String) ?? "") != "Complete"
                job.created = date(j["created"]) ?? date(j["startDate"]) ?? Date()
                job.contract = num(j["contract"])
                fillExtras(job, j)
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
                    item.sourceID = (p["id"] as? String) ?? ""
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

            // Punch details (priority, notes, value) and before/after photos — also added to jobs imported earlier.
            do {
                let mine = job.punchItems ?? []
                var bySID: [String: PunchItem] = [:]
                for it in mine where !it.sourceID.isEmpty { bySID[it.sourceID] = it }
                for p in punch where (p["jobId"] as? String) == jid {
                    let sid = str(p["id"])
                    if sid.isEmpty { continue }
                    var found = bySID[sid]
                    if found == nil {
                        let when = date(p["created"])
                        found = mine.first { $0.sourceID.isEmpty && $0.text == str(p["text"]) &&
                            (when == nil || abs($0.created.timeIntervalSince(when!)) < 2) }
                        if let f = found { f.sourceID = sid; bySID[sid] = f }
                    }
                    guard let item = found else { continue }
                    if item.priority.isEmpty { item.priority = str(p["priority"]) }
                    if item.extraNotes.isEmpty { item.extraNotes = str(p["extraNotes"]) }
                    if item.value == 0 { item.value = num(p["value"]) }
                    if !(item.photos ?? []).isEmpty { continue }
                    func add(_ list: Any?, _ kind: String) {
                        for e in (list as? [Any]) ?? [] {
                            let src = (e as? [String: Any])?["src"] ?? e
                            guard let bytes = photoData(src) else { continue }
                            let pp = PunchPhoto(data: bytes, kind: kind)
                            context.insert(pp)
                            pp.item = item
                            out.punchPhotos += 1
                        }
                    }
                    add(p["photosBefore"], "Before")
                    add(p["photosAfter"], "After")
                    if let c = p["completionPhoto"], !(c is NSNull) { add([c], "Completion") }
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
                k.startDate = date(c["startDate"]) ?? date(c["created"])
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

            for c in changeOrderList where (c["jobId"] as? String) == jid {
                let sid = (c["id"] as? String) ?? ""
                if sid.isEmpty || haveCO.contains(sid) { continue }
                let co = ChangeOrder(number: str(c["number"]))
                co.sourceID = sid
                co.title = str(c["title"])
                co.details = str(c["description"])
                co.amount = num(c["amount"])
                co.daysAdded = Int(num(c["daysAdded"]))
                co.status = str(c["status"]).isEmpty ? "Draft" : str(c["status"])
                co.reason = str(c["reason"]).isEmpty ? "Other" : str(c["reason"])
                co.date = date(c["date"]) ?? date(c["created"]) ?? Date()
                co.approvedBy = str(c["approvedBy"])
                co.approvedAt = date(c["approvedAt"])
                context.insert(co)
                co.job = job
                out.changeOrders += 1
            }

            for i in invoiceList where (i["jobId"] as? String) == jid {
                let sid = (i["id"] as? String) ?? ""
                if sid.isEmpty || haveInvoice.contains(sid) { continue }
                let inv = Invoice(title: str(i["desc"]), amount: num(i["amount"]))
                inv.sourceID = sid
                inv.date = date(i["date"]) ?? date(i["created"]) ?? Date()
                inv.status = str(i["status"]).isEmpty ? "Draft" : str(i["status"])
                inv.notes = str(i["notes"])
                context.insert(inv)
                inv.job = job
                out.invoices += 1
            }

            for p in permitList where (p["jobId"] as? String) == jid {
                let sid = (p["id"] as? String) ?? ""
                if sid.isEmpty || havePermit.contains(sid) { continue }
                let pm = Permit(trade: str(p["trade"]).isEmpty ? "General" : str(p["trade"]))
                pm.sourceID = sid
                pm.number = str(p["permitNumber"])
                pm.cost = num(p["cost"])
                pm.issueDate = date(p["issueDate"]) ?? date(p["created"]) ?? Date()
                pm.expirationDate = date(p["expirationDate"]) ?? pm.issueDate
                pm.status = str(p["status"]).isEmpty ? "Active" : str(p["status"])
                pm.notes = str(p["notes"])
                context.insert(pm)
                pm.job = job
                out.permits += 1
            }

            for t in timeList where (t["jobId"] as? String) == jid {
                let sid = (t["id"] as? String) ?? ""
                if sid.isEmpty || haveTime.contains(sid) { continue }
                let te = TimeEntry(worker: str(t["userName"]))
                te.sourceID = sid
                te.clockIn = date(t["clockIn"]) ?? Date()
                if let outAt = date(t["clockOut"]) { te.clockOut = outAt; te.isOpen = false } else { te.isOpen = true }
                te.rate = num(t["rate"])
                te.notes = str(t["notes"])
                context.insert(te)
                te.job = job
                out.timeEntries += 1
            }
            for a in apptList where (a["jobId"] as? String) == jid {
                let sid = str(a["id"])
                if sid.isEmpty || haveAppt.contains(sid) { continue }
                let ap = Appointment(title: str(a["title"]))
                ap.sourceID = sid
                ap.kind = str(a["type"]).isEmpty ? "Appointment" : str(a["type"])
                ap.notes = str(a["notes"])
                var when = date(a["date"]) ?? Date()
                let parts = str(a["time"]).split(separator: ":").compactMap { Int($0) }
                if parts.count >= 2, let t = Calendar.current.date(bySettingHour: parts[0], minute: parts[1], second: 0, of: when) { when = t }
                ap.date = when
                context.insert(ap)
                ap.job = job
                out.appointments += 1
            }

            for i in shopList where (i["jobId"] as? String) == jid {
                let sid = str(i["id"])
                if sid.isEmpty || haveShop.contains(sid) { continue }
                let it = ShoppingItem(text: str(i["text"]))
                it.sourceID = sid
                it.qty = num(i["qty"]) == 0 ? 1 : num(i["qty"])
                it.unit = str(i["unit"]) == "1" ? "" : str(i["unit"])
                it.price = num(i["price"])
                it.store = str(i["store"])
                it.note = str(i["note"])
                let b = str(i["bought"]).lowercased()
                it.bought = (b == "true" || b == "1")
                it.boughtAt = date(i["boughtAt"])
                it.created = date(i["created"]) ?? Date()
                context.insert(it)
                it.job = job
                out.shopping += 1
            }

            for d in docList where (d["jobId"] as? String) == jid {
                let sid = str(d["id"])
                if sid.isEmpty || haveDoc.contains(sid) { continue }
                let doc = JobDocument(name: str(d["name"]))
                doc.sourceID = sid
                doc.category = str(d["category"]).isEmpty ? "Other" : str(d["category"])
                doc.fileName = str(d["fileName"])
                doc.notes = str(d["notes"])
                doc.created = date(d["created"]) ?? Date()
                let src = str(d["fileSrc"])
                if src.hasPrefix("data:application/pdf") || str(d["fileType"]) == "pdf" { doc.ext = "pdf" } else { doc.ext = "jpg" }
                doc.data = photoData(src)
                context.insert(doc)
                doc.job = job
                out.documents += 1
            }
            for c in contractorList {
                let sid = (c["id"] as? String) ?? ""
                if sid.isEmpty { continue }
                if let k = ((try? context.fetch(FetchDescriptor<Contractor>())) ?? []).first(where: { $0.sourceID == sid }), k.startDate == nil {
                    k.startDate = date(c["startDate"]) ?? date(c["created"])
                }
            }
            try context.save()
        }
        return out
    }
}
