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

    private var expenses: [Expense] { (job.expenses ?? []).sorted { $0.date > $1.date } }
    private var contractors: [Contractor] { (job.contractors ?? []).sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending } }

    var body: some View {
        List {
            Section("Summary") {
                HStack {
                    Text("Contract")
                    Spacer()
                    TextField("0", value: $job.contract, format: .number)
                        .multilineTextAlignment(.trailing)
                        .frame(maxWidth: 140)
                }
                line("Expenses", job.expenseTotal, .orange)
                line("Contractors (agreed)", job.contractorTotal, .orange)
                line("Spent in total", job.totalCost, .red)
                line(job.remaining >= 0 ? "Remaining" : "Over budget", job.remaining, job.remaining >= 0 ? .blue : .red)
                if job.contract > 0 {
                    HStack { Text("Profit margin"); Spacer(); Text("\(job.marginPercent)%").bold() }
                }
                line("Paid to contractors so far", job.contractorPaid, .secondary)
                line("Still owed to contractors", job.contractorTotal - job.contractorPaid, .secondary)
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
        }
    }

    private func line(_ label: String, _ value: Double, _ color: Color) -> some View {
        HStack { Text(label); Spacer(); Text(Money.text(value)).bold().foregroundStyle(color) }
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
