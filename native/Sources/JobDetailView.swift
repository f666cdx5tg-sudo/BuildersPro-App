import SwiftUI
import SwiftData

enum Section3: String, CaseIterable, Identifiable {
    case spaces = "Spaces", punch = "Punch", photos = "Photos"
    var id: String { rawValue }
    var symbol: String { self == .spaces ? "square.grid.2x2" : self == .punch ? "checklist" : "photo.on.rectangle" }
}

/// Every tab on a job. Spaces / Punch / Photos reuse the space grid; Money and Reports have their own screens.
enum JobTab: String, CaseIterable, Identifiable {
    case spaces = "Spaces", punch = "Punch", photos = "Photos", money = "Money", reports = "Reports"
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
    @State private var tab: JobTab = .spaces
    @State private var addingSpace = false
    @State private var newSpace = ""

    var body: some View {
        VStack(spacing: 0) {
            // progress line: "91% (20/22) · 2 left"
            HStack {
                Text("Progress").font(.caption).foregroundStyle(.secondary)
                Spacer()
                Text("\(job.percent)% (\(job.doneCount)/\(job.totalCount))" +
                     (job.totalCount > job.doneCount ? " · \(job.totalCount - job.doneCount) left" : " ✓"))
                    .font(.caption.bold())
            }.padding(.horizontal).padding(.top, 8)

            Picker("Section", selection: $tab) {
                ForEach(JobTab.allCases) { Text($0.rawValue).tag($0) }
            }.pickerStyle(.segmented).padding()

            switch tab {
            case .money: MoneyView(job: job)
            case .reports: ReportsView(job: job)
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
                                Text(c.status).font(.caption).foregroundStyle(c.status == "Approved" ? Color.green : Color.secondary)
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
                                    .font(.caption).foregroundStyle(i.status == "Paid" ? Color.green : (i.status == "Overdue" ? Color.red : Color.secondary))
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
                                    .font(.caption).foregroundStyle(.secondary).lineLimit(1)
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
                                    .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 2) {
                                Text(Money.text(c.value)).bold()
                                Text(c.owed > 0.005 ? "\(Money.text(c.owed)) owed" : "paid")
                                    .font(.caption).foregroundStyle(c.owed > 0.005 ? Color.orange : Color.green)
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
                                    .font(.caption).foregroundStyle(p.status != "Closed" && p.expirationDate < Date() ? Color.red : Color.secondary)
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
                                    .font(.caption).foregroundStyle(t.isOpen ? Color.green : Color.secondary)
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
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .navigationTitle(order.number)
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
                            Text(r.date.formatted(date: .abbreviated, time: .omitted)).font(.caption).foregroundStyle(.secondary)
                        }
                        Text(r.completed.isEmpty ? "Nothing written yet" : r.completed)
                            .font(.subheadline).foregroundStyle(.secondary).lineLimit(2)
                        Text([r.workers > 0 ? "\(r.workers) worker(s)" : "", r.weather].filter { !$0.isEmpty }.joined(separator: " · "))
                            .font(.caption).foregroundStyle(.secondary)
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
    }

    private func notes(_ title: String, _ text: Binding<String>) -> some View {
        Section(title) { TextEditor(text: text).frame(minHeight: 70) }
    }
}
