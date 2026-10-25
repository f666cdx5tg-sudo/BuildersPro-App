import SwiftUI
import SwiftData
import UniformTypeIdentifiers
import ImageIO

// MARK: - Export everything to the web app's backup format (v5.40.1)
//
// One-way move out of this old native app into the web app (BuildersPro v6).
// It only READS this app's data — nothing here is changed or deleted.
// The file is the same shape the web app's "Save to iCloud" makes:
//   { app, version, exportedAt, db: { jobs:[…], rooms:[…], punchlist:[…], … } }
// and the web app's Sync → "Restore from iCloud" merges it in.
// Ids are stable (built from each record's own details), so exporting twice
// and restoring twice never makes duplicates.

enum BackupExporter {
    struct Counts {
        var jobs = 0, spaces = 0, punch = 0, photos = 0, punchPhotos = 0
        var expenses = 0, contractors = 0, payments = 0, reports = 0, changeOrders = 0
        var invoices = 0, permits = 0, time = 0, appointments = 0, notes = 0
        var shopping = 0, documents = 0, estimates = 0, contacts = 0, vendors = 0
        var check = ""
        var text: String {
            "\(jobs) jobs · \(spaces) spaces · \(punch) punch items · \(photos + punchPhotos) photos\n"
            + "\(changeOrders) change orders · \(expenses) expenses · \(contractors) contractors · \(payments) payments\n"
            + "\(reports) daily reports · \(invoices) invoices · \(permits) permits · \(time) time entries\n"
            + "\(appointments) appointments · \(notes) notes · \(shopping) shopping items · \(documents) documents\n"
            + "\(estimates) estimates · \(contacts) phone book contacts"
            + (check.isEmpty ? "" : "\n\n" + check)
        }
    }

    // ── formatting helpers ──
    private static let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]; return f
    }()
    private static let day: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.dateFormat = "yyyy-MM-dd"; return f
    }()
    private static let hm: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.dateFormat = "HH:mm"; return f
    }()
    private static func ts(_ d: Date?) -> Any { d.map { iso.string(from: $0) } ?? "" }
    private static func dayStr(_ d: Date?) -> Any { d.map { day.string(from: $0) } ?? "" }

    /// FNV-1a — a short, stable fingerprint so the same record always gets the same id.
    private static func hash(_ s: String) -> String {
        var h: UInt64 = 0xcbf29ce484222325
        for b in s.utf8 { h ^= UInt64(b); h = h &* 0x100000001b3 }
        return String(h, radix: 36)
    }
    private static func id(_ kind: String, _ source: String, _ parts: String...) -> String {
        if !source.isEmpty { return "nx" + kind + "_" + source }
        return "nx" + kind + "_" + hash(parts.joined(separator: "|"))
    }
    private static func ms(_ d: Date) -> String { String(Int64(d.timeIntervalSince1970 * 1000)) }

    /// Photos go out as JPEG data URLs, shrunk to 1600 px so the web app stays quick.
    private static func jpeg(_ d: Data?) -> String? {
        guard let d, let src = CGImageSourceCreateWithData(d as CFData, nil) else { return nil }
        let o: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true,
                                  kCGImageSourceCreateThumbnailWithTransform: true,
                                  kCGImageSourceThumbnailMaxPixelSize: 1600]
        guard let cg = CGImageSourceCreateThumbnailAtIndex(src, 0, o as CFDictionary) else { return nil }
        let out = NSMutableData()
        guard let dest = CGImageDestinationCreateWithData(out, UTType.jpeg.identifier as CFString, 1, nil) else { return nil }
        CGImageDestinationAddImage(dest, cg, [kCGImageDestinationLossyCompressionQuality: 0.75] as CFDictionary)
        guard CGImageDestinationFinalize(dest) else { return nil }
        return "data:image/jpeg;base64," + (out as Data).base64EncodedString()
    }
    private static func fileURL(_ d: Data?, ext: String) -> String {
        guard let d else { return "" }
        if ext.lowercased() == "pdf" { return "data:application/pdf;base64," + d.base64EncodedString() }
        return jpeg(d) ?? ""
    }

    // ── the export ──
    static func build(context: ModelContext) throws -> (Data, Counts) {
        var c = Counts()
        let now = iso.string(from: Date())
        func all<T: PersistentModel>(_ t: T.Type) -> [T] { (try? context.fetch(FetchDescriptor<T>())) ?? [] }

        var jobs: [[String: Any]] = [], rooms: [[String: Any]] = [], punch: [[String: Any]] = [], photos: [[String: Any]] = []
        var expenses: [[String: Any]] = [], contractors: [[String: Any]] = [], payments: [[String: Any]] = []
        var reports: [[String: Any]] = [], cos: [[String: Any]] = [], invoices: [[String: Any]] = [], permits: [[String: Any]] = []
        var time: [[String: Any]] = [], appts: [[String: Any]] = [], notes: [[String: Any]] = [], shopping: [[String: Any]] = []
        var docs: [[String: Any]] = [], estimates: [[String: Any]] = [], contacts: [[String: Any]] = [], vendors: [[String: Any]] = []

        for job in all(Job.self) {
            let jid = id("j", job.sourceID, job.name, ms(job.created))
            let status = job.status.isEmpty ? (job.isActive ? "Active" : "Complete") : job.status
            jobs.append(["id": jid, "name": job.name, "client": job.client, "clientEmail": job.clientEmail,
                         "clientPhone": job.clientPhone, "address": job.address, "city": "", "state": "", "zip": "",
                         "status": status, "contract": job.contract, "startDate": dayStr(job.startDate),
                         "completionDate": dayStr(job.completionDate), "notes": job.jobNotes,
                         "created": ts(job.created), "updatedAt": now, "importedFrom": "native 5.40"])
            c.jobs += 1

            // Spaces → rooms
            var roomId: [ObjectIdentifier: String] = [:]
            for s in job.spaces ?? [] {
                let rid = "nxr_" + s.uid.uuidString
                roomId[ObjectIdentifier(s)] = rid
                rooms.append(["id": rid, "jobId": jid, "name": s.name, "level": s.level, "order": s.order,
                              "space": s.isExterior ? "Exterior" : "Interior", "kind": "room",
                              "created": now, "updatedAt": now])
                c.spaces += 1
            }

            // Punch items, with their before / after / completion photos
            for p in job.punchItems ?? [] {
                var before: [[String: Any]] = [], after: [[String: Any]] = []
                var completion: Any = NSNull()
                for ph in (p.photos ?? []).sorted(by: { $0.created < $1.created }) {
                    guard let src = jpeg(ph.data) else { continue }
                    let entry: [String: Any] = ["src": src, "date": ts(ph.created)]
                    switch ph.kind {
                    case "After": after.append(entry)
                    case "Completion": completion = src
                    default: before.append(entry)
                    }
                    c.punchPhotos += 1
                }
                var row: [String: Any] = ["id": id("p", p.sourceID, jid, p.text, ms(p.created)), "jobId": jid,
                                          "roomId": p.space.flatMap { roomId[ObjectIdentifier($0)] } ?? "",
                                          "text": p.text, "trade": p.trade, "done": p.done,
                                          "created": ts(p.created), "updatedAt": now,
                                          "priority": p.priority, "extraNotes": p.extraNotes, "value": p.value,
                                          "photosBefore": before, "photosAfter": after, "completionPhoto": completion]
                if let done = p.completed { row["completedAt"] = ts(done) }
                punch.append(row)
                c.punch += 1
            }

            // Site photos
            for ph in job.photos ?? [] {
                guard let src = jpeg(ph.data) else { continue }
                photos.append(["id": "nxph_" + hash(jid + ms(ph.created) + ph.caption + String(ph.data?.count ?? 0)),
                               "jobId": jid, "roomId": ph.space.flatMap { roomId[ObjectIdentifier($0)] } ?? "",
                               "src": src, "caption": ph.caption, "date": ts(ph.created),
                               "created": ts(ph.created), "updatedAt": now])
                c.photos += 1
            }

            for e in job.expenses ?? [] {
                var row: [String: Any] = ["id": id("e", e.sourceID, jid, e.title, ms(e.date), String(e.amount)), "jobId": jid,
                                          "desc": e.title, "vendor": e.vendor, "category": e.category, "amount": e.amount,
                                          "date": dayStr(e.date), "created": ts(e.date), "updatedAt": now]
                let items: [[String: Any]] = e.itemsText.split(separator: "\n").map { line in
                    let parts = line.components(separatedBy: " — ")
                    let cost = Double(parts.count > 1 ? parts.last!.trimmingCharacters(in: .whitespaces) : "") ?? 0
                    return ["name": parts.first ?? String(line), "cost": cost]
                }
                if !items.isEmpty { row["items"] = items }
                if let r = jpeg(e.receipt) { row["receiptSrc"] = r }
                if !e.deliveryStatus.isEmpty {
                    row["isDelivery"] = true; row["deliveryStatus"] = e.deliveryStatus
                    row["poNumber"] = e.poNumber; row["timeWindow"] = e.timeWindow
                }
                expenses.append(row)
                c.expenses += 1
            }

            for k in job.contractors ?? [] {
                let kid = id("k", k.sourceID, jid, k.name, k.trade, String(k.value))
                contractors.append(["id": kid, "jobId": jid, "name": k.name, "trade": k.trade, "value": k.value,
                                    "scope": k.scope, "phone": k.phone, "status": k.status,
                                    "startDate": dayStr(k.startDate), "created": now, "updatedAt": now])
                c.contractors += 1
                for pay in k.payments ?? [] {
                    payments.append(["id": "nxpay_" + hash(kid + ms(pay.date) + String(pay.amount) + pay.method),
                                     "contractorId": kid, "jobId": jid, "amount": pay.amount, "date": dayStr(pay.date),
                                     "method": pay.method, "notes": pay.notes, "created": ts(pay.date), "updatedAt": now])
                    c.payments += 1
                }
            }

            for r in job.reports ?? [] {
                reports.append(["id": id("d", r.sourceID, jid, r.number, ms(r.date)), "jobId": jid, "dprNumber": r.number,
                                "date": dayStr(r.date), "workers": r.workers, "hours": r.hours, "weather": r.weather,
                                "completed": r.completed, "incomplete": r.incomplete, "tomorrow": r.tomorrow,
                                "visitors": r.visitors, "safety": r.safety, "clientNotes": r.clientNotes,
                                "progress": r.progress, "createdAt": ts(r.date), "created": ts(r.date), "updatedAt": now])
                c.reports += 1
            }

            for co in job.changeOrders ?? [] {
                cos.append(["id": id("c", co.sourceID, jid, co.number, co.title, ms(co.date)), "jobId": jid,
                            "number": co.number, "title": co.title, "description": co.details, "amount": co.amount,
                            "daysAdded": co.daysAdded, "status": co.status, "reason": co.reason,
                            "date": dayStr(co.date), "approvedBy": co.approvedBy, "approvedAt": ts(co.approvedAt),
                            "created": ts(co.date), "updatedAt": now])
                c.changeOrders += 1
            }

            for i in job.invoices ?? [] {
                invoices.append(["id": id("i", i.sourceID, jid, i.title, ms(i.date), String(i.amount)), "jobId": jid,
                                 "desc": i.title, "amount": i.amount, "date": dayStr(i.date), "status": i.status,
                                 "notes": i.notes, "created": ts(i.date), "updatedAt": now])
                c.invoices += 1
            }

            for p in job.permits ?? [] {
                permits.append(["id": id("m", p.sourceID, jid, p.trade, p.number, ms(p.issueDate)), "jobId": jid,
                                "trade": p.trade, "permitNumber": p.number, "cost": p.cost,
                                "issueDate": dayStr(p.issueDate), "expirationDate": dayStr(p.expirationDate),
                                "status": p.status, "notes": p.notes, "created": ts(p.issueDate), "updatedAt": now])
                c.permits += 1
            }

            for t in job.timeEntries ?? [] {
                time.append(["id": id("t", t.sourceID, jid, t.worker, ms(t.clockIn)), "jobId": jid, "userName": t.worker,
                             "date": dayStr(t.clockIn), "clockIn": ts(t.clockIn), "clockOut": t.isOpen ? "" : ts(t.clockOut),
                             "rate": t.rate, "notes": t.notes, "created": ts(t.clockIn), "updatedAt": now])
                c.time += 1
            }

            for a in job.appointments ?? [] {
                appts.append(["id": id("a", a.sourceID, jid, a.title, ms(a.date)), "jobId": jid, "title": a.title,
                              "type": a.kind, "date": dayStr(a.date), "time": hm.string(from: a.date),
                              "notes": a.notes, "created": now, "updatedAt": now])
                c.appointments += 1
            }

            for n in job.notes ?? [] {
                notes.append(["id": id("n", n.sourceID, jid, n.title, ms(n.created)), "jobId": jid, "roomId": "",
                              "title": n.title, "text": n.text, "createdBy": n.author,
                              "created": ts(n.created), "updatedAt": now])
                c.notes += 1
            }

            for s in job.shopping ?? [] {
                var row: [String: Any] = ["id": id("s", s.sourceID, jid, s.text, ms(s.created)), "jobId": jid, "text": s.text,
                                          "qty": s.qty, "unit": s.unit, "price": s.price, "store": s.store, "note": s.note,
                                          "bought": s.bought, "created": ts(s.created), "updatedAt": now]
                if let b = s.boughtAt { row["boughtAt"] = ts(b) }
                shopping.append(row)
                c.shopping += 1
            }

            for d in job.documents ?? [] {
                let isPDF = d.ext.lowercased() == "pdf"
                docs.append(["id": id("f", d.sourceID, jid, d.name, ms(d.created)), "jobId": jid, "name": d.name,
                             "category": d.category, "fileName": d.fileName.isEmpty ? d.name + "." + d.ext : d.fileName,
                             "fileType": isPDF ? "pdf" : "image", "fileSrc": fileURL(d.data, ext: d.ext),
                             "notes": d.notes, "created": ts(d.created), "updatedAt": now])
                c.documents += 1
            }
        }

        for e in all(Estimate.self) {
            estimates.append(["id": id("q", e.sourceID, e.title, ms(e.created)), "title": e.title, "client": e.client,
                              "clientEmail": e.clientEmail, "status": e.status,
                              "lineItems": e.lines.map { ["desc": $0.desc, "qty": $0.qty, "price": $0.price] },
                              "notes": e.notes, "created": ts(e.created), "updatedAt": now])
            c.estimates += 1
        }

        for b in all(BookContact.self) {
            let skills = b.skills.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
            contacts.append(["id": "nxb_" + hash(b.name + "|" + b.company + "|" + ms(b.created)), "type": "Contractor",
                             "name": b.name, "company": b.company, "phone": b.phone, "email": b.email,
                             "skills": skills, "rating": b.rating > 0 ? "up" : (b.rating < 0 ? "down" : ""),
                             "notes": b.notes, "jobId": "", "created": ts(b.created), "updated": now, "updatedAt": now])
            c.contacts += 1
        }

        for v in all(Vendor.self) {
            vendors.append(["id": id("v", v.sourceID, v.name), "name": v.name, "created": now, "updatedAt": now])
            c.vendors += 1
        }

        // v5.40.2: two records can share an id (copied items keep the same source id, or were made
        // in the same millisecond). The web app merges by id, so a shared id silently drops one.
        // Give every repeat its own id.
        func uniq(_ rows: inout [[String: Any]]) {
            var seen = Set<String>()
            for i in rows.indices {
                guard let base = rows[i]["id"] as? String else { continue }
                var cand = base, n = 2
                while seen.contains(cand) { cand = base + "_" + String(n); n += 1 }
                seen.insert(cand)
                rows[i]["id"] = cand
            }
        }
        uniq(&jobs); uniq(&rooms); uniq(&punch); uniq(&photos); uniq(&expenses); uniq(&contractors); uniq(&payments)
        uniq(&reports); uniq(&cos); uniq(&invoices); uniq(&permits); uniq(&time); uniq(&appts); uniq(&notes)
        uniq(&shopping); uniq(&docs); uniq(&estimates); uniq(&contacts); uniq(&vendors)

        // A check line per job, to compare against the web app after the restore.
        c.check = all(Job.self).map { j in
            let open = (j.punchItems ?? []).filter { !$0.done }.count
            return "\(j.name): \(open) open of \(j.totalCount) · left \(Money.text(j.remaining))"
        }.joined(separator: "\n")

        let db: [String: Any] = ["jobs": jobs, "rooms": rooms, "punchlist": punch, "photos": photos,
                                 "expenses": expenses, "contractors": contractors, "payments": payments,
                                 "reports": reports, "changeOrders": cos, "invoices": invoices, "permits": permits,
                                 "timeEntries": time, "appointments": appts, "jobNotes": notes, "shopping": shopping,
                                 "documents": docs, "estimates": estimates, "contacts": contacts, "vendors": vendors]
        let root: [String: Any] = ["app": "BuildersPro", "version": "native-5.40.1", "exportedAt": now,
                                   "note": "Everything from the old BuildersPro native app. Restore it in the web app with Sync → Restore from iCloud.",
                                   "db": db]
        let data = try JSONSerialization.data(withJSONObject: root, options: [])
        return (data, c)
    }
}

/// The file handed to the share sheet / Files.
struct BackupJSONFile: FileDocument {
    static var readableContentTypes: [UTType] { [.json] }
    var data: Data
    init(data: Data) { self.data = data }
    init(configuration: ReadConfiguration) throws { data = configuration.file.regularFileContents ?? Data() }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper { FileWrapper(regularFileWithContents: data) }
}

/// "Export everything" button + the save dialog. Shown on the Jobs screen and in the "+" menu.
struct ExportToWebButton: View {
    @Environment(\.modelContext) private var context
    @State private var file: BackupJSONFile?
    @State private var saving = false
    @State private var working = false
    @State private var counts = BackupExporter.Counts()
    @State private var message = ""
    @State private var showMessage = false

    private var fileName: String {
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd-HHmm"
        return "BuildersPro-native-export-" + f.string(from: Date())
    }

    var body: some View {
        Button { run() } label: {
            HStack(spacing: 10) {
                Image(systemName: working ? "hourglass" : "square.and.arrow.up")
                Text(working ? "Preparing your jobs…" : "Export everything to the web app").font(.headline.weight(.heavy))
            }
            .frame(maxWidth: .infinity, minHeight: 50)
            .foregroundStyle(.white)
            .background(Color(red: 0.04, green: 0.52, blue: 1.0), in: RoundedRectangle(cornerRadius: 14))
        }
        .buttonStyle(.plain)
        .disabled(working)
        .fileExporter(isPresented: $saving, document: file, contentType: .json, defaultFilename: fileName) { result in
            switch result {
            case .success: message = "Saved.\n\n" + counts.text + "\n\nNow open the web app → Sync → Restore from iCloud and pick this file."
            case .failure(let e): message = "Not saved: " + e.localizedDescription
            }
            showMessage = true
        }
        .alert("Export", isPresented: $showMessage) { Button("OK", role: .cancel) {} } message: { Text(message) }
    }

    private func run() {
        working = true
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 200_000_000)
            do {
                let (data, c) = try BackupExporter.build(context: context)
                counts = c
                file = BackupJSONFile(data: data)
                saving = true
            } catch {
                message = "Could not build the export: " + error.localizedDescription
                showMessage = true
            }
            working = false
        }
    }
}
