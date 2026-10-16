import SwiftUI
import SwiftData
import UniformTypeIdentifiers
import PDFKit

enum Section3: String, CaseIterable, Identifiable {
    case spaces = "Spaces", punch = "Punch", photos = "Photos"
    var id: String { rawValue }
    var symbol: String { self == .spaces ? "square.grid.2x2" : self == .punch ? "checklist" : "photo.on.rectangle" }
}

/// Every tab on a job. Spaces / Punch / Photos reuse the space grid; Money and Reports have their own screens.
enum JobTab: String, CaseIterable, Identifiable {
    case spaces = "Spaces", punch = "Punch", photos = "Photos", money = "Money", reports = "Reports",
         schedule = "Schedule", notes = "Notes", shopping = "Shopping", docs = "Docs"
    var id: String { rawValue }
    var grid: Section3? {
        switch self {
        case .spaces: return .spaces
        case .punch: return .punch
        case .photos: return .photos
        default: return nil
        }
    }
}

struct JobDetailView: View {
    @Environment(\.modelContext) private var context
    @Bindable var job: Job
    @State private var tab: JobTab
    @State private var addingSpace = false
    @State private var newSpace = ""

    init(job: Job, start: JobTab = .spaces) {
        _job = Bindable(job)
        _tab = State(initialValue: start)
    }

    var body: some View {
        VStack(spacing: 0) {
            // progress line: "91% (20/22) · 2 left"
            HStack {
                Text("Progress").font(.callout).foregroundStyle(.secondary)
                Spacer()
                Text("\(job.percent)% (\(job.doneCount)/\(job.totalCount))" +
                     (job.totalCount > job.doneCount ? " · \(job.totalCount - job.doneCount) left" : " ✓"))
                    .font(.callout.bold())
            }.padding(.horizontal).padding(.top, 8)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(JobTab.allCases) { t in
                        Button { tab = t } label: {
                            Text(t.rawValue).font(.body.weight(.semibold))
                                .padding(.horizontal, 14).padding(.vertical, 7)
                                .background(tab == t ? Color.accentColor : Color.gray.opacity(0.15), in: Capsule())
                                .foregroundStyle(tab == t ? Color.white : Color.primary)
                        }.buttonStyle(.plain)
                    }
                }.padding(.horizontal).padding(.vertical, 10)
            }

            switch tab {
            case .money: MoneyView(job: job)
            case .reports: ReportsView(job: job)
            case .schedule: ScheduleView(job: job)
            case .notes: NotesView(job: job)
            case .shopping: ShoppingView(job: job)
            case .docs: DocsView(job: job)
            default: SpaceGrid(job: job, mode: tab.grid ?? .spaces)
            }
        }
        .navigationTitle(job.name)
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .toolbar {
            // one button holds the options (standing rule)
            Menu {
                Button("Add a space", systemImage: "plus.square") { addingSpace = true }
                Button("Add an expense", systemImage: "dollarsign.circle") { addExpense() }
                Button("Add a contractor", systemImage: "person.badge.plus") { addContractor() }
                Button("Add a change order", systemImage: "arrow.triangle.2.circlepath") { addChangeOrder() }
                Button("Add an invoice", systemImage: "doc.plaintext") { addInvoice() }
                Button("Add a permit", systemImage: "checkmark.seal") { addPermit() }
                Button("Clock in (labor)", systemImage: "clock") { clockIn() }
                Button("Add a daily report", systemImage: "doc.text") { addReport() }
                Button("Add an appointment", systemImage: "calendar.badge.plus") { addAppointment() }
                Button("Add a note", systemImage: "note.text.badge.plus") { addNote() }
                Button("Add a shopping item", systemImage: "cart.badge.plus") { addShopping() }
            } label: { Image(systemName: "line.3.horizontal") }
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
        tab = .spaces
    }

    // These three create a blank record and jump to its tab; tap the new row to fill it in.
    private func addExpense() {
        let e = Expense(title: "New expense", amount: 0)
        context.insert(e); e.job = job
        tab = .money
    }
    private func addContractor() {
        let c = Contractor(name: "New contractor")
        context.insert(c); c.job = job
        tab = .money
    }
    private func addChangeOrder() {
        let n = ((job.changeOrders ?? []).count) + 1
        let c = ChangeOrder(number: String(format: "CO-%03d", n))
        c.title = "New change order"
        context.insert(c); c.job = job
        tab = .money
    }
    private func addInvoice() {
        let i = Invoice(title: "New invoice", amount: 0)
        context.insert(i); i.job = job
        tab = .money
    }
    private func addPermit() {
        let p = Permit(trade: "General")
        context.insert(p); p.job = job
        tab = .money
    }
    private func clockIn() {
        if (job.timeEntries ?? []).contains(where: { $0.isOpen }) { tab = .money; return }   // already clocked in
        let t = TimeEntry(worker: "")
        t.clockIn = Date(); t.isOpen = true
        context.insert(t); t.job = job
        tab = .money
    }
    private func addAppointment() {
        let a = Appointment(title: "New appointment")
        context.insert(a); a.job = job
        tab = .schedule
    }
    private func addNote() {
        let n = JobNote(title: "New note")
        context.insert(n); n.job = job
        tab = .notes
    }
    private func addShopping() {
        let i = ShoppingItem(text: "New item")
        context.insert(i); i.job = job
        tab = .shopping
    }
    private func addReport() {
        let n = (job.reports ?? []).count + 1
        let r = DailyReport(number: String(format: "DPR-%03d", n))
        context.insert(r); r.job = job
        tab = .reports
    }
}

// MARK: - Money

struct MoneyView: View {
    @Environment(\.modelContext) private var context
    @Bindable var job: Job

    private var changeOrders: [ChangeOrder] { (job.changeOrders ?? []).sorted { $0.number < $1.number } }
    private var invoices: [Invoice] { (job.invoices ?? []).sorted { $0.date > $1.date } }
    private var expenses: [Expense] { (job.expenses ?? []).sorted { $0.date > $1.date } }
    private var contractors: [Contractor] { (job.contractors ?? []).sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending } }
    private var permits: [Permit] { (job.permits ?? []).sorted { $0.expirationDate < $1.expirationDate } }
    private var timeEntries: [TimeEntry] { (job.timeEntries ?? []).sorted { $0.clockIn > $1.clockIn } }

    var body: some View {
        List {
            if job.revisedContract > 0 && job.remaining < 0 {
                Text("Over budget by \(Money.text(-job.remaining)) (costs \(Money.text(job.totalCost)) vs contract \(Money.text(job.revisedContract)))")
                    .font(.subheadline.weight(.bold)).foregroundStyle(Color.red)
            }

            Section("Contract") {
                HStack {
                    Text("Original contract")
                    Spacer()
                    TextField("0", value: $job.contract, format: .number)
                        .multilineTextAlignment(.trailing)
                        .frame(maxWidth: 140)
                }
                line("Approved change orders", job.approvedChangeOrders, job.approvedChangeOrders < 0 ? .orange : .green)
                line("Revised contract", job.revisedContract, .blue)
                if job.pendingChangeOrders != 0 { line("Pending change orders (not counted)", job.pendingChangeOrders, .secondary) }
            }

            Section("Profit") {
                line("Expenses", job.expenseTotal, .orange)
                line("Contractors (agreed)", job.contractorTotal, .orange)
                line("Total cost", job.totalCost, .red)
                line(job.remaining >= 0 ? "Remaining" : "Over budget", job.remaining, job.remaining >= 0 ? .blue : .red)
                if job.revisedContract > 0 {
                    HStack { Text("Profit margin"); Spacer(); Text("\(job.marginPercent)%").bold() }
                }
            }

            Section("Billing") {
                line("Invoiced", job.invoiced, .primary)
                line("Collected", job.collected, .green)
                line("Waiting to be paid", job.outstanding, .orange)
            }

            Section("Cash out the door") {
                line("Expenses", job.expenseTotal, .secondary)
                line("Paid to contractors", job.contractorPaid, .secondary)
                line("Permits", job.permitTotal, .secondary)
                line("Time-clock labor (\(String(format: "%.1f", job.laborHours)) h)", job.laborTotal, .secondary)
                line("Total spent", job.cashSpent, .red)
                line("Still owed to contractors", job.contractorTotal - job.contractorPaid, .secondary)
            }

            Section("Change orders · \(changeOrders.count)") {
                if changeOrders.isEmpty { Text("None. Use ≡ → Add a change order.").foregroundStyle(.secondary) }
                ForEach(changeOrders) { c in
                    NavigationLink { ChangeOrderDetail(order: c) } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(c.number) · \(c.title)").lineLimit(1)
                                Text(c.status).font(.callout).foregroundStyle(c.status == "Approved" ? Color.green : Color.secondary)
                            }
                            Spacer()
                            Text(Money.text(c.amount)).bold()
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(changeOrders[$0]) } }
            }

            Section("Invoices · \(Money.text(job.invoiced))") {
                if invoices.isEmpty { Text("None. Use ≡ → Add an invoice.").foregroundStyle(.secondary) }
                ForEach(invoices) { i in
                    NavigationLink { InvoiceDetail(invoice: i) } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(i.title.isEmpty ? "Invoice" : i.title).lineLimit(1)
                                Text("\(i.status) · \(i.date.formatted(date: .abbreviated, time: .omitted))")
                                    .font(.callout).foregroundStyle(i.status == "Paid" ? Color.green : (i.status == "Overdue" ? Color.red : Color.secondary))
                            }
                            Spacer()
                            Text(Money.text(i.amount)).bold()
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(invoices[$0]) } }
            }

            Section("Expenses · \(Money.text(job.expenseTotal))") {
                if expenses.isEmpty { Text("No expenses yet. Use ≡ → Add an expense.").foregroundStyle(.secondary) }
                ForEach(expenses) { e in
                    NavigationLink { ExpenseDetail(expense: e) } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(e.title.isEmpty ? "Expense" : e.title).lineLimit(1)
                                Text([e.vendor, e.category].filter { !$0.isEmpty }.joined(separator: " · "))
                                    .font(.callout).foregroundStyle(.secondary).lineLimit(1)
                            }
                            Spacer()
                            if e.receipt != nil { Image(systemName: "paperclip").foregroundStyle(.secondary) }
                            Text(Money.text(e.amount)).bold()
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(expenses[$0]) } }
            }

            Section("Contractors · \(Money.text(job.contractorTotal))") {
                if contractors.isEmpty { Text("No contractors yet. Use ≡ → Add a contractor.").foregroundStyle(.secondary) }
                ForEach(contractors) { c in
                    NavigationLink { ContractorDetail(contractor: c) } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(c.name).lineLimit(1)
                                Text([c.trade, c.status].filter { !$0.isEmpty }.joined(separator: " · "))
                                    .font(.callout).foregroundStyle(.secondary).lineLimit(1)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 2) {
                                Text(Money.text(c.value)).bold()
                                Text(c.owed > 0.005 ? "\(Money.text(c.owed)) owed" : "paid")
                                    .font(.callout).foregroundStyle(c.owed > 0.005 ? Color.orange : Color.green)
                            }
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(contractors[$0]) } }
            }

            Section("Permits · \(Money.text(job.permitTotal))") {
                if permits.isEmpty { Text("None. Use ≡ → Add a permit.").foregroundStyle(.secondary) }
                ForEach(permits) { p in
                    NavigationLink { PermitDetail(permit: p) } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(p.trade) \(p.number)").lineLimit(1)
                                Text("\(p.status) · expires \(p.expirationDate.formatted(date: .abbreviated, time: .omitted))")
                                    .font(.callout).foregroundStyle(p.status != "Closed" && p.expirationDate < Date() ? Color.red : Color.secondary)
                            }
                            Spacer()
                            Text(Money.text(p.cost)).bold()
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(permits[$0]) } }
            }

            Section("Time clock · \(String(format: "%.1f", job.laborHours)) h · \(Money.text(job.laborTotal))") {
                if timeEntries.isEmpty { Text("None. Use ≡ → Clock in (labor).").foregroundStyle(.secondary) }
                ForEach(timeEntries) { t in
                    NavigationLink { TimeEntryDetail(entry: t) } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(t.worker.isEmpty ? "Worker" : t.worker).lineLimit(1)
                                Text(t.clockIn.formatted(date: .abbreviated, time: .shortened) + (t.isOpen ? " · clocked in" : ""))
                                    .font(.callout).foregroundStyle(t.isOpen ? Color.green : Color.secondary)
                            }
                            Spacer()
                            Text("\(String(format: "%.2f", t.hours)) h").bold()
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(timeEntries[$0]) } }
            }
        }
    }

    private func line(_ label: String, _ value: Double, _ color: Color) -> some View {
        HStack { Text(label); Spacer(); Text(Money.text(value)).bold().foregroundStyle(color) }
    }
}

struct ChangeOrderDetail: View {
    @Bindable var order: ChangeOrder

    var body: some View {
        Form {
            Section("Change order") {
                TextField("Number", text: $order.number)
                TextField("Title", text: $order.title)
                Picker("Status", selection: $order.status) {
                    ForEach(Money.coStatuses, id: \.self) { Text($0).tag($0) }
                }
                .onChange(of: order.status) { _, new in order.approvedAt = (new == "Approved") ? (order.approvedAt ?? Date()) : nil }
                Picker("Reason", selection: $order.reason) {
                    if !Money.coReasons.contains(order.reason) { Text(order.reason).tag(order.reason) }
                    ForEach(Money.coReasons, id: \.self) { Text($0).tag($0) }
                }
                TextField("Amount (negative = credit)", value: $order.amount, format: .number)
                Stepper("Days added: \(order.daysAdded)", value: $order.daysAdded, in: -365...365)
                DatePicker("Date", selection: $order.date, displayedComponents: .date)
                TextField("Approved by", text: $order.approvedBy)
            }
            Section("Scope of the change") { TextEditor(text: $order.details).frame(minHeight: 90) }
            Section {
                Text(order.status == "Approved" ? "Counted in the revised contract." : "Not counted until it is Approved.")
                    .font(.callout).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .navigationTitle(order.number)
        .pdfExport(name: "\(order.number) change order") {
            let j = order.job
            return DocSheet(heading: "Change order \(order.number)", sub: order.title, job: j,
                rows: [("Status", order.status), ("Reason", order.reason),
                       ("Date", order.date.formatted(date: .long, time: .omitted)),
                       ("Amount", Money.text(order.amount)), ("Days added", "\(order.daysAdded)"),
                       ("Approved by", order.approvedBy),
                       ("Original contract", Money.text(j?.contract ?? 0)),
                       ("Revised contract", Money.text(j?.revisedContract ?? 0))],
                sections: [("Scope of the change", order.details)])
        }
    }
}

struct InvoiceDetail: View {
    @Bindable var invoice: Invoice

    var body: some View {
        Form {
            Section("Invoice") {
                TextField("Description", text: $invoice.title)
                TextField("Amount", value: $invoice.amount, format: .number)
                Picker("Status", selection: $invoice.status) {
                    ForEach(Money.invoiceStatuses, id: \.self) { Text($0).tag($0) }
                }
                DatePicker("Date", selection: $invoice.date, displayedComponents: .date)
            }
            Section("Notes") { TextEditor(text: $invoice.notes).frame(minHeight: 70) }
        }
        .formStyle(.grouped)
        .navigationTitle(invoice.title.isEmpty ? "Invoice" : invoice.title)
        .pdfExport(name: "Invoice " + (invoice.title.isEmpty ? "" : invoice.title)) {
            let j = invoice.job
            return DocSheet(heading: "Invoice", sub: invoice.title, job: j,
                rows: [("Date", invoice.date.formatted(date: .long, time: .omitted)),
                       ("Status", invoice.status), ("Amount due", Money.text(invoice.amount)),
                       ("Revised contract", Money.text(j?.revisedContract ?? 0)),
                       ("Invoiced to date", Money.text(j?.invoiced ?? 0)),
                       ("Collected", Money.text(j?.collected ?? 0)),
                       ("Outstanding", Money.text(j?.outstanding ?? 0))],
                sections: [("Notes", invoice.notes)])
        }
    }
}

struct PermitDetail: View {
    @Bindable var permit: Permit

    var body: some View {
        Form {
            Section("Permit") {
                Picker("Trade", selection: $permit.trade) {
                    if !Money.permitTrades.contains(permit.trade) { Text(permit.trade).tag(permit.trade) }
                    ForEach(Money.permitTrades, id: \.self) { Text($0).tag($0) }
                }
                TextField("Permit number", text: $permit.number)
                TextField("Cost", value: $permit.cost, format: .number)
                Picker("Status", selection: $permit.status) {
                    ForEach(Money.permitStatuses, id: \.self) { Text($0).tag($0) }
                }
                DatePicker("Issued", selection: $permit.issueDate, displayedComponents: .date)
                DatePicker("Expires", selection: $permit.expirationDate, displayedComponents: .date)
            }
            Section("Notes") { TextEditor(text: $permit.notes).frame(minHeight: 70) }
        }
        .formStyle(.grouped)
        .navigationTitle("\(permit.trade) permit")
    }
}

struct TimeEntryDetail: View {
    @Bindable var entry: TimeEntry

    var body: some View {
        Form {
            Section("Time entry") {
                TextField("Worker", text: $entry.worker)
                TextField("Hourly rate", value: $entry.rate, format: .number)
                DatePicker("Clock in", selection: $entry.clockIn)
                Toggle("Still clocked in", isOn: $entry.isOpen)
                if !entry.isOpen { DatePicker("Clock out", selection: $entry.clockOut) }
                if entry.isOpen {
                    Button("Clock out now", systemImage: "stop.circle") { entry.clockOut = Date(); entry.isOpen = false }
                }
            }
            Section("Totals") {
                HStack { Text("Hours"); Spacer(); Text(String(format: "%.2f", entry.hours)).bold() }
                HStack { Text("Labor cost"); Spacer(); Text(Money.text(entry.hours * entry.rate)).bold() }
            }
            Section("Notes") { TextEditor(text: $entry.notes).frame(minHeight: 60) }
        }
        .formStyle(.grouped)
        .navigationTitle(entry.worker.isEmpty ? "Time entry" : entry.worker)
    }
}

struct ExpenseDetail: View {
    @Bindable var expense: Expense

    var body: some View {
        Form {
            Section("Expense") {
                TextField("What was it", text: $expense.title)
                TextField("Vendor", text: $expense.vendor)
                Picker("Category", selection: $expense.category) {
                    if !Money.categories.contains(expense.category) { Text(expense.category.isEmpty ? "None" : expense.category).tag(expense.category) }
                    ForEach(Money.categories, id: \.self) { Text($0).tag($0) }
                }
                TextField("Amount", value: $expense.amount, format: .number)
                DatePicker("Date", selection: $expense.date, displayedComponents: .date)
            }
            if !expense.itemsText.isEmpty {
                Section("Items") { Text(expense.itemsText) }
            }
            if let d = expense.receipt, let img = PhotoThumb.image(d) {
                Section("Receipt") { img.resizable().scaledToFit() }
            }
        }
        .formStyle(.grouped)
        .navigationTitle(expense.title.isEmpty ? "Expense" : expense.title)
    }
}

struct ContractorDetail: View {
    @Environment(\.modelContext) private var context
    @Bindable var contractor: Contractor

    private var payments: [Payment] { (contractor.payments ?? []).sorted { $0.date > $1.date } }

    var body: some View {
        Form {
            Section("Contractor") {
                TextField("Name", text: $contractor.name)
                TextField("Trade", text: $contractor.trade)
                TextField("Phone", text: $contractor.phone)
                Picker("Status", selection: $contractor.status) {
                    if !["Active", "Completed"].contains(contractor.status) { Text(contractor.status).tag(contractor.status) }
                    Text("Active").tag("Active")
                    Text("Completed").tag("Completed")
                }
                TextField("Agreed amount", value: $contractor.value, format: .number)
            }
            Section("Scope of work") {
                TextEditor(text: $contractor.scope).frame(minHeight: 80)
            }
            Section("Payments · paid \(Money.text(contractor.paid)) of \(Money.text(contractor.value))") {
                ForEach(payments) { p in PaymentRow(payment: p) }
                    .onDelete { idx in idx.forEach { context.delete(payments[$0]) } }
                Button("Add a payment", systemImage: "plus.circle") {
                    let p = Payment(amount: 0)
                    context.insert(p); p.contractor = contractor
                }
            }
        }
        .formStyle(.grouped)
        .navigationTitle(contractor.name)
    }
}

struct PaymentRow: View {
    @Bindable var payment: Payment
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                TextField("Amount", value: $payment.amount, format: .number)
                Picker("Method", selection: $payment.method) {
                    if !Money.methods.contains(payment.method) { Text(payment.method).tag(payment.method) }
                    ForEach(Money.methods, id: \.self) { Text($0).tag($0) }
                }.labelsHidden()
            }
            DatePicker("Date", selection: $payment.date, displayedComponents: .date)
            TextField("Note", text: $payment.notes)
        }
    }
}

// MARK: - Daily reports

struct ReportsView: View {
    @Environment(\.modelContext) private var context
    @Bindable var job: Job

    private var reports: [DailyReport] { (job.reports ?? []).sorted { $0.date > $1.date } }

    var body: some View {
        List {
            if reports.isEmpty { Text("No daily reports yet. Use ≡ → Add a daily report.").foregroundStyle(.secondary) }
            ForEach(reports) { r in
                NavigationLink { ReportDetail(report: r) } label: {
                    VStack(alignment: .leading, spacing: 3) {
                        HStack {
                            Text(r.number.isEmpty ? "Daily report" : r.number).font(.headline)
                            Spacer()
                            Text(r.date.formatted(date: .abbreviated, time: .omitted)).font(.callout).foregroundStyle(.secondary)
                        }
                        Text(r.completed.isEmpty ? "Nothing written yet" : r.completed)
                            .font(.body).foregroundStyle(.secondary).lineLimit(2)
                        Text([r.workers > 0 ? "\(r.workers) worker(s)" : "", r.weather].filter { !$0.isEmpty }.joined(separator: " · "))
                            .font(.callout).foregroundStyle(.secondary)
                    }
                }
            }
            .onDelete { idx in idx.forEach { context.delete(reports[$0]) } }
        }
    }
}

struct ReportDetail: View {
    @Bindable var report: DailyReport

    var body: some View {
        Form {
            Section("Report") {
                TextField("Report number", text: $report.number)
                DatePicker("Date", selection: $report.date, displayedComponents: .date)
                Stepper("Workers on site: \(report.workers)", value: $report.workers, in: 0...200)
                TextField("Hours", text: $report.hours)
                TextField("Weather", text: $report.weather)
                Stepper("Job progress: \(report.progress)%", value: $report.progress, in: 0...100)
            }
            notes("Work completed", $report.completed)
            notes("Not finished", $report.incomplete)
            notes("Planned for tomorrow", $report.tomorrow)
            notes("Visitors", $report.visitors)
            notes("Safety", $report.safety)
            notes("Notes for the client", $report.clientNotes)
        }
        .formStyle(.grouped)
        .navigationTitle(report.number.isEmpty ? "Daily report" : report.number)
        .pdfExport(name: "Daily report " + report.number) {
            DocSheet(heading: "Daily report " + report.number, sub: report.date.formatted(date: .complete, time: .omitted), job: report.job,
                rows: [("Workers on site", "\(report.workers)"), ("Hours", report.hours), ("Weather", report.weather),
                       ("Job progress", "\(report.progress)%")],
                sections: [("Work completed", report.completed), ("Not finished", report.incomplete),
                           ("Planned for tomorrow", report.tomorrow), ("Visitors", report.visitors),
                           ("Safety", report.safety), ("Notes for the client", report.clientNotes)])
        }
    }

    private func notes(_ title: String, _ text: Binding<String>) -> some View {
        Section(title) { TextEditor(text: text).frame(minHeight: 70) }
    }
}


// MARK: - Schedule

struct ScheduleView: View {
    @Environment(\.modelContext) private var context
    @Bindable var job: Job
    @State private var month = Calendar.current.date(from: Calendar.current.dateComponents([.year, .month], from: Date())) ?? Date()
    @State private var picked: Date? = Calendar.current.startOfDay(for: Date())

    private var cal: Calendar { Calendar.current }
    private var all: [Appointment] { (job.appointments ?? []).sorted { $0.date < $1.date } }

    private func count(on day: Date) -> Int { all.filter { cal.isDate($0.date, inSameDayAs: day) }.count }

    /// Every cell of the month grid, with blanks (nil) before the 1st.
    private var cells: [Date?] {
        guard let range = cal.range(of: .day, in: .month, for: month) else { return [] }
        let lead = cal.component(.weekday, from: month) - cal.firstWeekday
        let blanks = (lead + 7) % 7
        var out: [Date?] = Array(repeating: nil, count: blanks)
        for d in range { out.append(cal.date(byAdding: .day, value: d - 1, to: month)) }
        return out
    }

    private var shown: [Appointment] {
        guard let d = picked else { return all }
        return all.filter { cal.isDate($0.date, inSameDayAs: d) }
    }

    var body: some View {
        List {
            Section {
                HStack {
                    Button { shift(-1) } label: { Image(systemName: "chevron.left") }.buttonStyle(.plain)
                    Spacer()
                    Text(month.formatted(.dateTime.month(.wide).year())).font(.title3.bold())
                    Spacer()
                    Button { shift(1) } label: { Image(systemName: "chevron.right") }.buttonStyle(.plain)
                }
                let cols = Array(repeating: GridItem(.flexible(), spacing: 4), count: 7)
                LazyVGrid(columns: cols, spacing: 4) {
                    ForEach(Array(cal.veryShortWeekdaySymbols.enumerated()), id: \.offset) { _, d in
                        Text(d).font(.callout).foregroundStyle(.secondary)
                    }
                    ForEach(Array(cells.enumerated()), id: \.offset) { _, day in
                        if let day {
                            let n = count(on: day)
                            let isPicked = picked.map { cal.isDate($0, inSameDayAs: day) } ?? false
                            Button { picked = isPicked ? nil : cal.startOfDay(for: day) } label: {
                                VStack(spacing: 2) {
                                    Text("\(cal.component(.day, from: day))")
                                        .font(.body.weight(cal.isDateInToday(day) ? .bold : .regular))
                                    Circle().fill(n > 0 ? Color.orange : Color.clear).frame(width: 7, height: 7)
                                }
                                .frame(maxWidth: .infinity, minHeight: 44)
                                .background(isPicked ? Color.accentColor.opacity(0.35) : (cal.isDateInToday(day) ? Color.gray.opacity(0.2) : Color.clear),
                                            in: RoundedRectangle(cornerRadius: 8))
                            }.buttonStyle(.plain)
                        } else {
                            Color.clear.frame(height: 44)
                        }
                    }
                }
            }
            Section(picked.map { $0.formatted(date: .complete, time: .omitted) } ?? "All appointments") {
                if shown.isEmpty { Text(picked == nil ? "Nothing scheduled. Use ≡ → Add an appointment." : "Nothing this day. Tap the day again to see all.").foregroundStyle(.secondary) }
                ForEach(shown) { a in
                    NavigationLink { AppointmentDetail(item: a) } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(a.title.isEmpty ? "Appointment" : a.title).font(.headline)
                            Text(a.date.formatted(date: picked == nil ? .abbreviated : .omitted, time: .shortened) + " · " + a.kind)
                                .font(.callout).foregroundStyle(.secondary)
                        }
                    }
                }
                .onDelete { idx in idx.forEach { context.delete(shown[$0]) } }
            }
        }
    }

    private func shift(_ by: Int) {
        if let m = cal.date(byAdding: .month, value: by, to: month) { month = m }
    }
}

struct AppointmentDetail: View {
    @Bindable var item: Appointment
    var body: some View {
        Form {
            TextField("Title", text: $item.title)
            Picker("Type", selection: $item.kind) { ForEach(Money.appointmentKinds, id: \.self) { Text($0).tag($0) } }
            DatePicker("When", selection: $item.date)
            Section("Notes") { TextEditor(text: $item.notes).frame(minHeight: 90) }
        }
        .formStyle(.grouped)
        .navigationTitle(item.title.isEmpty ? "Appointment" : item.title)
    }
}

// MARK: - Notes

struct NotesView: View {
    @Environment(\.modelContext) private var context
    @Bindable var job: Job
    private var items: [JobNote] { (job.notes ?? []).sorted { $0.created > $1.created } }

    var body: some View {
        List {
            if items.isEmpty { Text("No notes yet. Use ≡ → Add a note.").foregroundStyle(.secondary) }
            ForEach(items) { n in
                NavigationLink { NoteDetail(item: n) } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(n.title.isEmpty ? "Note" : n.title).font(.headline)
                        Text(n.text.isEmpty ? "Empty" : n.text).font(.body).foregroundStyle(.secondary).lineLimit(2)
                        Text(n.created.formatted(date: .abbreviated, time: .omitted)).font(.callout).foregroundStyle(.secondary)
                    }
                }
            }
            .onDelete { idx in idx.forEach { context.delete(items[$0]) } }
        }
    }
}

struct NoteDetail: View {
    @Bindable var item: JobNote
    var body: some View {
        Form {
            TextField("Title", text: $item.title)
            TextField("Written by", text: $item.author)
            Section("Note") { TextEditor(text: $item.text).frame(minHeight: 200) }
        }
        .formStyle(.grouped)
        .navigationTitle(item.title.isEmpty ? "Note" : item.title)
    }
}

// MARK: - Shopping

struct ShoppingView: View {
    @Environment(\.modelContext) private var context
    @Bindable var job: Job
    private var toBuy: [ShoppingItem] { (job.shopping ?? []).filter { !$0.bought }.sorted { $0.created < $1.created } }
    private var bought: [ShoppingItem] { (job.shopping ?? []).filter { $0.bought }.sorted { ($0.boughtAt ?? .distantPast) > ($1.boughtAt ?? .distantPast) } }

    var body: some View {
        List {
            if (job.shopping ?? []).isEmpty { Text("Nothing on the list. Use ≡ → Add a shopping item.").foregroundStyle(.secondary) }
            if !toBuy.isEmpty {
                Section("To buy · est. " + Money.text(toBuy.reduce(0) { $0 + $1.total })) { rows(toBuy) }
            }
            if !bought.isEmpty {
                Section("Bought · " + Money.text(bought.reduce(0) { $0 + $1.total })) { rows(bought) }
            }
        }
    }

    @ViewBuilder private func rows(_ items: [ShoppingItem]) -> some View {
        ForEach(items) { i in
            HStack {
                Button {
                    i.bought.toggle(); i.boughtAt = i.bought ? Date() : nil
                } label: {
                    Image(systemName: i.bought ? "checkmark.circle.fill" : "circle").font(.title3)
                        .foregroundStyle(i.bought ? Color.green : Color.secondary)
                }.buttonStyle(.plain)
                NavigationLink { ShoppingDetail(item: i) } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(i.text.isEmpty ? "Item" : i.text).strikethrough(i.bought)
                        Text([i.qty != 1 ? "\(i.qty.formatted()) \(i.unit)" : "", i.store, i.total > 0 ? Money.text(i.total) : ""]
                                .filter { !$0.isEmpty }.joined(separator: " · "))
                            .font(.callout).foregroundStyle(.secondary)
                    }
                }
            }
        }
        .onDelete { idx in idx.forEach { context.delete(items[$0]) } }
    }
}

struct ShoppingDetail: View {
    @Bindable var item: ShoppingItem
    @Query(sort: \Vendor.name) private var vendors: [Vendor]
    var body: some View {
        Form {
            TextField("Item", text: $item.text)
            HStack { Text("Quantity"); Spacer(); TextField("1", value: $item.qty, format: .number).multilineTextAlignment(.trailing).frame(width: 90) }
            TextField("Unit (ea, box, ft…)", text: $item.unit)
            HStack { Text("Price each"); Spacer(); TextField("0", value: $item.price, format: .number).multilineTextAlignment(.trailing).frame(width: 110) }
            TextField("Store / vendor", text: $item.store)
            if !vendors.isEmpty {
                Picker("Pick a vendor", selection: $item.store) {
                    Text("—").tag(item.store)
                    ForEach(vendors) { Text($0.name).tag($0.name) }
                }
            }
            Toggle("Bought", isOn: $item.bought)
                .onChange(of: item.bought) { _, now in item.boughtAt = now ? Date() : nil }
            TextField("Note", text: $item.note, axis: .vertical)
            Text("Total: " + Money.text(item.total)).foregroundStyle(.secondary)
        }
        .formStyle(.grouped)
        .navigationTitle(item.text.isEmpty ? "Item" : item.text)
    }
}

// MARK: - Documents

struct PDFBox: View {
    let data: Data
    var body: some View { PDFRep(data: data) }
}
#if os(iOS)
struct PDFRep: UIViewRepresentable {
    let data: Data
    func makeUIView(context: Context) -> PDFView { let v = PDFView(); v.autoScales = true; v.document = PDFDocument(data: data); return v }
    func updateUIView(_ v: PDFView, context: Context) {}
}
#else
struct PDFRep: NSViewRepresentable {
    let data: Data
    func makeNSView(context: Context) -> PDFView { let v = PDFView(); v.autoScales = true; v.document = PDFDocument(data: data); return v }
    func updateNSView(_ v: PDFView, context: Context) {}
}
#endif

struct DocsView: View {
    @Environment(\.modelContext) private var context
    @Bindable var job: Job
    @State private var picking = false
    @State private var message = ""
    private var items: [JobDocument] { (job.documents ?? []).sorted { $0.created > $1.created } }

    var body: some View {
        List {
            Button { picking = true } label: { Label("Add a document (PDF or picture)", systemImage: "doc.badge.plus") }
            if items.isEmpty { Text("No documents yet.").foregroundStyle(.secondary) }
            ForEach(items) { d in
                NavigationLink { DocDetail(item: d) } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(d.name.isEmpty ? "Document" : d.name).font(.headline)
                        Text(d.category + " · " + d.created.formatted(date: .abbreviated, time: .omitted))
                            .font(.callout).foregroundStyle(.secondary)
                    }
                }
            }
            .onDelete { idx in idx.forEach { context.delete(items[$0]) } }
        }
        .fileImporter(isPresented: $picking, allowedContentTypes: [.pdf, .image]) { result in
            guard case .success(let url) = result else { return }
            let ok = url.startAccessingSecurityScopedResource()
            defer { if ok { url.stopAccessingSecurityScopedResource() } }
            guard let data = try? Data(contentsOf: url) else { return }
            let d = JobDocument(name: url.deletingPathExtension().lastPathComponent)
            d.fileName = url.lastPathComponent
            d.ext = url.pathExtension.lowercased()
            d.data = data
            context.insert(d); d.job = job
        }
    }
}

struct DocDetail: View {
    @Bindable var item: JobDocument
    var body: some View {
        Form {
            TextField("Name", text: $item.name)
            Picker("Category", selection: $item.category) { ForEach(Money.documentCategories, id: \.self) { Text($0).tag($0) } }
            TextField("Notes", text: $item.notes, axis: .vertical)
            Section("Preview") {
                if let d = item.data {
                    if item.ext == "pdf" { PDFBox(data: d).frame(height: 460) }
                    else if let img = PhotoThumb.image(d) { img.resizable().scaledToFit() }
                    else { Text("Can't preview this file type.").foregroundStyle(.secondary) }
                } else {
                    Text("No file attached.").foregroundStyle(.secondary)
                }
            }
        }
        .formStyle(.grouped)
        .navigationTitle(item.name.isEmpty ? "Document" : item.name)
    }
}


// MARK: - PDF export (daily report, invoice, change order)

struct PDFFile: FileDocument {
    static var readableContentTypes: [UTType] { [.pdf] }
    var data: Data
    init(data: Data) { self.data = data }
    init(configuration: ReadConfiguration) throws { data = configuration.file.regularFileContents ?? Data() }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper { FileWrapper(regularFileWithContents: data) }
}

/// One printable page: company line, title, job, a table of facts, then written sections.
struct DocSheet: View {
    let heading: String
    let sub: String
    let job: Job?
    let rows: [(String, String)]
    let sections: [(String, String)]

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("BuildersPro").font(.system(size: 11, weight: .heavy)).foregroundStyle(.gray)
                Spacer()
                Text(Date().formatted(date: .abbreviated, time: .omitted)).font(.system(size: 11)).foregroundStyle(.gray)
            }
            Text(heading).font(.system(size: 26, weight: .heavy))
            if !sub.isEmpty { Text(sub).font(.system(size: 15)).foregroundStyle(.gray) }
            if let job {
                VStack(alignment: .leading, spacing: 2) {
                    Text(job.name).font(.system(size: 14, weight: .bold))
                    if !job.address.isEmpty { Text(job.address).font(.system(size: 12)).foregroundStyle(.gray) }
                    if !job.client.isEmpty { Text("Client: " + job.client).font(.system(size: 12)).foregroundStyle(.gray) }
                }
            }
            Divider()
            VStack(spacing: 6) {
                ForEach(Array(rows.filter { !$0.1.isEmpty }.enumerated()), id: \.offset) { _, r in
                    HStack(alignment: .top) {
                        Text(r.0).font(.system(size: 12, weight: .semibold)).frame(width: 150, alignment: .leading)
                        Text(r.1).font(.system(size: 12))
                        Spacer()
                    }
                }
            }
            ForEach(Array(sections.filter { !$0.1.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }.enumerated()), id: \.offset) { _, sec in
                VStack(alignment: .leading, spacing: 4) {
                    Text(sec.0.uppercased()).font(.system(size: 10, weight: .heavy)).foregroundStyle(.gray)
                    Text(sec.1).font(.system(size: 12)).fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .padding(40)
        .frame(width: 612, alignment: .topLeading)
        .foregroundStyle(Color.black)
        .background(Color.white)
        .environment(\.colorScheme, .light)
    }
}

@MainActor func makePDF<V: View>(_ view: V) -> Data? {
    let renderer = ImageRenderer(content: view)
    let out = NSMutableData()
    var ok = false
    renderer.render { size, draw in
        var box = CGRect(origin: .zero, size: CGSize(width: max(size.width, 612), height: max(size.height, 792)))
        guard let consumer = CGDataConsumer(data: out as CFMutableData),
              let ctx = CGContext(consumer: consumer, mediaBox: &box, nil) else { return }
        ctx.beginPDFPage(nil)
        ctx.translateBy(x: 0, y: box.height - size.height)      // keep the content at the top of the page
        draw(ctx)
        ctx.endPDFPage(); ctx.closePDF()
        ok = true
    }
    return ok ? out as Data : nil
}

struct PDFExportModifier: ViewModifier {
    let name: String
    let sheet: @MainActor () -> DocSheet
    @State private var exporting = false
    @State private var file = PDFFile(data: Data())

    func body(content: Content) -> some View {
        content
            .toolbar {
                Button {
                    file = PDFFile(data: makePDF(sheet()) ?? Data())
                    exporting = true
                } label: { Label("Make PDF", systemImage: "arrow.down.doc") }
            }
            .fileExporter(isPresented: $exporting, document: file, contentType: .pdf,
                          defaultFilename: name.trimmingCharacters(in: .whitespaces)) { _ in }
    }
}

extension View {
    func pdfExport(name: String, sheet: @escaping @MainActor () -> DocSheet) -> some View {
        modifier(PDFExportModifier(name: name, sheet: sheet))
    }
}
