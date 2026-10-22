import SwiftUI
import SwiftData
#if os(iOS)
import ARKit
import SceneKit
import CoreMotion
import AVFoundation
#endif

// MARK: - Tools hub (AR Measure · Level · Color match · Contractors)

struct ToolsView: View {
    @AppStorage("bpDark") private var dark = true
    var body: some View {
        List {
            #if os(iOS)
            NavigationLink { ARMeasureView() } label: { row("ruler", "AR Measure", "Point the camera, tap two points", Theme.sky) }
            NavigationLink { LevelView() } label: { row("level", "Level", "Bubble level in degrees and in/ft", Theme.green) }
            NavigationLink { ColorMatchView() } label: { row("eyedropper", "Color match", "Sample a wall color with the camera", Theme.orange) }
            #endif
            NavigationLink { ContractorBookView() } label: { row("person.2.crop.square.stack", "Contractors", "Address book with skills and thumbs", Theme.gold) }
        }
        .navigationTitle("Tools")
    }
    private func row(_ symbol: String, _ title: String, _ sub: String, _ c: Color) -> some View {
        HStack(spacing: 14) {
            Image(systemName: symbol).font(.title2).foregroundStyle(c).frame(width: 36)
            VStack(alignment: .leading, spacing: 2) { Text(title).font(.headline); Text(sub).font(.callout).foregroundStyle(.secondary) }
        }.padding(.vertical, 4)
    }
}

/// Feet-and-inches text for a length in meters, to the nearest 1/8".
func feetInches(_ meters: Double) -> String {
    let eighths = Int((meters * 39.3701 * 8).rounded())
    let ft = eighths / 96, rem = eighths % 96, inch = rem / 8, frac = rem % 8
    let fr = ["", "⅛", "¼", "⅜", "½", "⅝", "¾", "⅞"][frac]
    return ft > 0 ? "\(ft)′ \(inch)\(fr)″" : "\(inch)\(fr)″"
}

#if os(iOS)
// MARK: - AR Measure

struct ARMeasureView: View {
    @State private var segments: [Double] = []
    @State private var status = "Move the phone slowly to find a surface"
    @State private var undoTick = 0, clearTick = 0
    private var total: Double { segments.reduce(0, +) }

    var body: some View {
        ZStack(alignment: .bottom) {
            if ARWorldTrackingConfiguration.isSupported {
                ARMeasureRep(segments: $segments, status: $status, undoTick: undoTick, clearTick: clearTick).ignoresSafeArea()
                Image(systemName: "plus").font(.system(size: 34, weight: .light)).foregroundStyle(.white).shadow(radius: 3)
                    .frame(maxHeight: .infinity)
            } else {
                Text("AR isn't supported on this device.").foregroundStyle(.secondary).frame(maxHeight: .infinity)
            }
            VStack(spacing: 10) {
                Text(status).font(.footnote.weight(.semibold)).padding(.horizontal, 12).padding(.vertical, 6).background(.ultraThinMaterial, in: Capsule())
                if let last = segments.last {
                    VStack(spacing: 2) {
                        Text(feetInches(last)).font(.system(size: 34, weight: .heavy, design: .rounded))
                        if segments.count > 1 { Text("Total " + feetInches(total)).font(.callout).foregroundStyle(.secondary) }
                    }
                }
                HStack(spacing: 10) {
                    Button { undoTick += 1 } label: { Label("Undo", systemImage: "arrow.uturn.backward").frame(maxWidth: .infinity) }
                    Button(role: .destructive) { clearTick += 1; segments = [] } label: { Label("Clear", systemImage: "trash").frame(maxWidth: .infinity) }
                }.buttonStyle(.borderedProminent).controlSize(.large)
            }
            .padding(14).background(.bar)
        }
        .navigationTitle("AR Measure").navigationBarTitleDisplayMode(.inline)
    }
}

struct ARMeasureRep: UIViewRepresentable {
    @Binding var segments: [Double]
    @Binding var status: String
    var undoTick: Int, clearTick: Int

    func makeCoordinator() -> Coord { Coord(self) }
    func makeUIView(context: Context) -> ARSCNView {
        let v = ARSCNView()
        v.automaticallyUpdatesLighting = true
        v.session.delegate = context.coordinator
        let cfg = ARWorldTrackingConfiguration(); cfg.planeDetection = [.horizontal, .vertical]
        v.session.run(cfg)
        v.addGestureRecognizer(UITapGestureRecognizer(target: context.coordinator, action: #selector(Coord.tap(_:))))
        context.coordinator.view = v
        return v
    }
    func updateUIView(_ v: ARSCNView, context: Context) {
        let c = context.coordinator; c.parent = self
        if undoTick != c.lastUndo { c.lastUndo = undoTick; c.undo() }
        if clearTick != c.lastClear { c.lastClear = clearTick; c.clear() }
    }
    static func dismantleUIView(_ v: ARSCNView, coordinator: Coord) { v.session.pause() }

    final class Coord: NSObject, ARSessionDelegate {
        var parent: ARMeasureRep
        weak var view: ARSCNView?
        var lastUndo = 0, lastClear = 0
        var points: [SCNNode] = [], lines: [SCNNode] = [], labels: [SCNNode] = []
        init(_ p: ARMeasureRep) { parent = p }

        func session(_ session: ARSession, didUpdate frame: ARFrame) {
            if case .normal = frame.camera.trackingState { if parent.status.hasPrefix("Move") { DispatchQueue.main.async { self.parent.status = "Aim at a corner and tap to drop a point" } } }
        }

        @objc func tap(_ g: UITapGestureRecognizer) {
            guard let v = view else { return }
            let pt = CGPoint(x: v.bounds.midX, y: v.bounds.midY)   // crosshair is always the center
            guard let q = v.raycastQuery(from: pt, allowing: .estimatedPlane, alignment: .any),
                  let hit = v.session.raycast(q).first else { parent.status = "No surface found — move closer or add light"; return }
            let t = hit.worldTransform.columns.3
            let pos = SCNVector3(t.x, t.y, t.z)
            let dot = SCNNode(geometry: SCNSphere(radius: 0.006)); dot.geometry?.firstMaterial?.diffuse.contents = UIColor.systemYellow
            dot.position = pos; v.scene.rootNode.addChildNode(dot)
            if let prev = points.last {
                let d = Double(distance(prev.position, pos))
                let line = lineNode(prev.position, pos); v.scene.rootNode.addChildNode(line); lines.append(line)
                let lab = labelNode(feetInches(d), at: SCNVector3((prev.position.x + pos.x) / 2, (prev.position.y + pos.y) / 2 + 0.02, (prev.position.z + pos.z) / 2))
                v.scene.rootNode.addChildNode(lab); labels.append(lab)
                parent.segments.append(d)
            }
            points.append(dot)
            parent.status = "Tap again to keep measuring, or Clear to start over"
        }
        func undo() {
            guard let p = points.popLast() else { return }
            p.removeFromParentNode()
            if let l = lines.popLast() { l.removeFromParentNode() }
            if let l = labels.popLast() { l.removeFromParentNode() }
            if !parent.segments.isEmpty { parent.segments.removeLast() }
        }
        func clear() { (points + lines + labels).forEach { $0.removeFromParentNode() }; points = []; lines = []; labels = [] }

        private func distance(_ a: SCNVector3, _ b: SCNVector3) -> Float { sqrtf((a.x-b.x)*(a.x-b.x) + (a.y-b.y)*(a.y-b.y) + (a.z-b.z)*(a.z-b.z)) }
        private func lineNode(_ a: SCNVector3, _ b: SCNVector3) -> SCNNode {
            let h = CGFloat(distance(a, b))
            let cyl = SCNCylinder(radius: 0.002, height: h); cyl.firstMaterial?.diffuse.contents = UIColor.systemYellow
            let n = SCNNode(geometry: cyl)
            n.position = SCNVector3((a.x+b.x)/2, (a.y+b.y)/2, (a.z+b.z)/2)
            n.look(at: b, up: SCNVector3(0, 1, 0), localFront: SCNVector3(0, 1, 0))
            return n
        }
        private func labelNode(_ s: String, at p: SCNVector3) -> SCNNode {
            let t = SCNText(string: s, extrusionDepth: 0.1); t.font = .boldSystemFont(ofSize: 10); t.firstMaterial?.diffuse.contents = UIColor.white
            let n = SCNNode(geometry: t); n.scale = SCNVector3(0.004, 0.004, 0.004); n.position = p
            n.constraints = [SCNBillboardConstraint()]
            let (mn, mx) = t.boundingBox; n.pivot = SCNMatrix4MakeTranslation((mx.x - mn.x) / 2, 0, 0)
            return n
        }
    }
}

// MARK: - Level

final class LevelMotion: ObservableObject {
    private let mm = CMMotionManager()
    @Published var gx = 0.0, gy = 0.0, gz = -1.0
    func start() {
        guard mm.isDeviceMotionAvailable else { return }
        mm.deviceMotionUpdateInterval = 1 / 30
        mm.startDeviceMotionUpdates(to: .main) { [weak self] m, _ in
            guard let g = m?.gravity else { return }
            self?.gx = g.x; self?.gy = g.y; self?.gz = g.z
        }
    }
    func stop() { mm.stopDeviceMotionUpdates() }
}

struct LevelView: View {
    @StateObject private var mo = LevelMotion()
    @State private var zeroX = 0.0, zeroY = 0.0, zeroEdge = 0.0
    private var flat: Bool { abs(mo.gz) > 0.8 }
    private var edgeRaw: Double { atan2(mo.gx, -mo.gy) * 180 / .pi }
    private var edgeDev: Double { let r = edgeRaw - (edgeRaw / 90).rounded() * 90; return r - zeroEdge }
    private var tiltX: Double { mo.gx - zeroX }
    private var tiltY: Double { mo.gy - zeroY }
    private var deg: Double { flat ? asin(min(1, sqrt(tiltX * tiltX + tiltY * tiltY))) * 180 / .pi : abs(edgeDev) }
    private var inPerFt: Double { tan(deg * .pi / 180) * 12 }
    private var isLevel: Bool { deg < 0.3 }

    var body: some View {
        VStack(spacing: 24) {
            Text(flat ? "Phone flat on the surface" : "Hold the phone's edge against the surface").font(.callout).foregroundStyle(.secondary)
            if flat {
                ZStack {
                    Circle().stroke(Color.secondary, lineWidth: 3).frame(width: 260, height: 260)
                    Circle().stroke(Color.secondary.opacity(0.4)).frame(width: 40, height: 40)
                    Circle().fill(isLevel ? Theme.green : Theme.orange).frame(width: 44, height: 44)
                        .offset(x: max(-108, min(108, -tiltX * 900)), y: max(-108, min(108, tiltY * 900)))
                }.frame(height: 270)
            } else {
                ZStack {
                    RoundedRectangle(cornerRadius: 20).stroke(Color.secondary, lineWidth: 3).frame(width: 300, height: 56)
                    Rectangle().fill(Color.secondary.opacity(0.5)).frame(width: 2, height: 56)
                    Circle().fill(isLevel ? Theme.green : Theme.orange).frame(width: 44, height: 44)
                        .offset(x: max(-125, min(125, edgeDev * 12)))
                }.frame(height: 270)
            }
            Text(String(format: "%.1f°", deg)).font(.system(size: 64, weight: .heavy, design: .rounded)).foregroundStyle(isLevel ? Theme.green : .primary)
            Text(isLevel ? "LEVEL" : String(format: "%.2f in per foot", inPerFt)).font(.title3.weight(.bold)).foregroundStyle(isLevel ? Theme.green : Theme.orange)
            Button("Zero here") { zeroX = mo.gx; zeroY = mo.gy; zeroEdge = edgeRaw - (edgeRaw / 90).rounded() * 90 }
                .buttonStyle(.borderedProminent).controlSize(.large)
            Spacer()
        }
        .padding(.top, 20).frame(maxWidth: .infinity)
        .navigationTitle("Level").navigationBarTitleDisplayMode(.inline)
        .onAppear { mo.start() }.onDisappear { mo.stop() }
    }
}

// MARK: - Color match

final class ColorSampler: NSObject, ObservableObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let session = AVCaptureSession()
    @Published var rgb: (Double, Double, Double) = (0.5, 0.5, 0.5)
    private let q = DispatchQueue(label: "color.sampler")
    private var configured = false
    func start() {
        AVCaptureDevice.requestAccess(for: .video) { ok in
            guard ok else { return }
            self.q.async {
                if !self.configured {
                    self.configured = true
                    guard let dev = AVCaptureDevice.default(for: .video), let inp = try? AVCaptureDeviceInput(device: dev) else { return }
                    self.session.beginConfiguration()
                    if self.session.canAddInput(inp) { self.session.addInput(inp) }
                    let out = AVCaptureVideoDataOutput()
                    out.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
                    out.setSampleBufferDelegate(self, queue: self.q)
                    if self.session.canAddOutput(out) { self.session.addOutput(out) }
                    self.session.commitConfiguration()
                }
                self.session.startRunning()
            }
        }
    }
    func stop() { q.async { self.session.stopRunning() } }
    func captureOutput(_ o: AVCaptureOutput, didOutput sb: CMSampleBuffer, from c: AVCaptureConnection) {
        guard let px = CMSampleBufferGetImageBuffer(sb) else { return }
        CVPixelBufferLockBaseAddress(px, .readOnly); defer { CVPixelBufferUnlockBaseAddress(px, .readOnly) }
        guard let base = CVPixelBufferGetBaseAddress(px)?.assumingMemoryBound(to: UInt8.self) else { return }
        let w = CVPixelBufferGetWidth(px), h = CVPixelBufferGetHeight(px), bpr = CVPixelBufferGetBytesPerRow(px)
        var r = 0.0, g = 0.0, b = 0.0, n = 0.0
        for y in stride(from: h / 2 - 20, to: h / 2 + 20, by: 2) { for x in stride(from: w / 2 - 20, to: w / 2 + 20, by: 2) {
            let p = base + y * bpr + x * 4; b += Double(p[0]); g += Double(p[1]); r += Double(p[2]); n += 1 } }
        let v = (r / n / 255, g / n / 255, b / n / 255)
        DispatchQueue.main.async { self.rgb = v }
    }
}

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession
    final class V: UIView { override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self } }
    func makeUIView(context: Context) -> V { let v = V(); (v.layer as! AVCaptureVideoPreviewLayer).session = session; (v.layer as! AVCaptureVideoPreviewLayer).videoGravity = .resizeAspectFill; return v }
    func updateUIView(_ v: V, context: Context) {}
}

struct ColorMatchView: View {
    @StateObject private var cam = ColorSampler()
    @State private var white: (Double, Double, Double)? = nil
    @State private var a: (Double, Double, Double)? = nil
    @State private var b: (Double, Double, Double)? = nil

    private func corrected(_ c: (Double, Double, Double)) -> (Double, Double, Double) {
        guard let w = white else { return c }
        let m = max(w.0, w.1, w.2, 0.01)
        return (min(1, c.0 / max(w.0, 0.01) * m), min(1, c.1 / max(w.1, 0.01) * m), min(1, c.2 / max(w.2, 0.01) * m))
    }
    private var cur: (Double, Double, Double) { corrected(cam.rgb) }
    private func hex(_ c: (Double, Double, Double)) -> String { String(format: "#%02X%02X%02X", Int(c.0 * 255 + 0.5), Int(c.1 * 255 + 0.5), Int(c.2 * 255 + 0.5)) }
    private func col(_ c: (Double, Double, Double)) -> Color { Color(red: c.0, green: c.1, blue: c.2) }
    /// Rough perceptual difference (redmean) 0 = identical, ~100+ = clearly different
    private func delta(_ x: (Double, Double, Double), _ y: (Double, Double, Double)) -> Double {
        let rm = (x.0 + y.0) / 2 * 255, dr = (x.0 - y.0) * 255, dg = (x.1 - y.1) * 255, db = (x.2 - y.2) * 255
        return sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db) / 7.6
    }
    private func slot(_ title: String, _ v: (Double, Double, Double)?, set: @escaping () -> Void) -> some View {
        Button(action: set) {
            VStack(spacing: 4) {
                RoundedRectangle(cornerRadius: 10).fill(v.map(col) ?? Color.secondary.opacity(0.2)).frame(height: 44)
                Text(v.map(hex) ?? title).font(.caption.weight(.bold)).foregroundStyle(.primary)
            }
        }.buttonStyle(.plain).frame(maxWidth: .infinity)
    }

    var body: some View {
        VStack(spacing: 0) {
            ZStack {
                CameraPreview(session: cam.session)
                Circle().stroke(.white, lineWidth: 3).frame(width: 44, height: 44).shadow(radius: 3)
            }.frame(maxHeight: .infinity)
            VStack(spacing: 12) {
                HStack(spacing: 14) {
                    RoundedRectangle(cornerRadius: 12).fill(col(cur)).frame(width: 70, height: 70)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(hex(cur)).font(.title.weight(.heavy))
                        Text("R \(Int(cur.0 * 255))  G \(Int(cur.1 * 255))  B \(Int(cur.2 * 255))").font(.callout).foregroundStyle(.secondary)
                        if white != nil { Text("White reference applied").font(.caption).foregroundStyle(Theme.green) }
                    }
                    Spacer()
                }
                HStack(spacing: 10) {
                    slot("Save A") { a = cur }
                    slot("Save B") { b = cur }
                    Button { white = cam.rgb } label: { Text(white == nil ? "Set white" : "Reset").font(.subheadline.weight(.bold)).frame(maxWidth: .infinity, minHeight: 44) }
                        .buttonStyle(.bordered).simultaneousGesture(TapGesture().onEnded { if white != nil { white = nil } })
                }
                if let a, let b {
                    let d = delta(a, b)
                    Text(d < 4 ? "Very close match" : d < 12 ? "Close — slight difference" : "Visibly different")
                        .font(.headline).foregroundStyle(d < 4 ? Theme.green : d < 12 ? Theme.orange : Theme.red)
                }
                Text("Tip: point at white paper first and tap Set white — it cancels out room lighting.").font(.caption).foregroundStyle(.secondary)
            }.padding(14).background(.bar)
        }
        .navigationTitle("Color match").navigationBarTitleDisplayMode(.inline)
        .onAppear { cam.start() }.onDisappear { cam.stop() }
    }
}
#endif

// MARK: - Contractor address book

@Model
final class BookContact {
    var name: String = ""
    var company: String = ""
    var phone: String = ""
    var email: String = ""
    var skills: String = ""        // comma-separated trades, e.g. "Plumbing, Gas"
    var rating: Int = 0            // 1 = thumbs up, -1 = thumbs down, 0 = none
    var notes: String = ""
    var created: Date = Date()
    init(name: String) { self.name = name }
}

struct ContractorBookView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \BookContact.name) private var all: [BookContact]
    @State private var search = ""
    @State private var skill = "All skills"
    @State private var editing: BookContact?

    private var skillList: [String] {
        let s = Set(all.flatMap { $0.skills.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) } }.filter { !$0.isEmpty })
        return ["All skills"] + s.sorted()
    }
    private var shown: [BookContact] {
        all.filter { c in
            (skill == "All skills" || c.skills.localizedCaseInsensitiveContains(skill)) &&
            (search.isEmpty || [c.name, c.company, c.skills, c.phone].contains { $0.localizedCaseInsensitiveContains(search) })
        }
    }

    var body: some View {
        List {
            Section {
                Picker("Skill", selection: $skill) { ForEach(skillList, id: \.self) { Text($0) } }
            }
            if shown.isEmpty { Text("No contractors yet. Tap + to add one.").foregroundStyle(.secondary) }
            ForEach(shown) { c in
                Button { editing = c } label: {
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(c.name.isEmpty ? "Unnamed" : c.name).font(.headline).foregroundStyle(.primary)
                            if !c.company.isEmpty { Text(c.company).font(.callout).foregroundStyle(.secondary) }
                            if !c.skills.isEmpty { Text(c.skills).font(.caption.weight(.bold)).foregroundStyle(Theme.gold) }
                            if !c.phone.isEmpty { Label(c.phone, systemImage: "phone").font(.callout).foregroundStyle(Theme.blue) }
                        }
                        Spacer()
                        if c.rating != 0 { Image(systemName: c.rating > 0 ? "hand.thumbsup.fill" : "hand.thumbsdown.fill").foregroundStyle(c.rating > 0 ? Theme.green : Theme.red) }
                    }
                }
            }.onDelete { idx in idx.forEach { context.delete(shown[$0]) } }
        }
        .searchable(text: $search, prompt: "Search name, company, skill")
        .navigationTitle("Contractors")
        .toolbar { ToolbarItem(placement: .primaryAction) { Button { let c = BookContact(name: ""); context.insert(c); editing = c } label: { Image(systemName: "plus") } } }
        .sheet(item: $editing) { c in ContractorEditor(c: c) }
    }
}

struct ContractorEditor: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var c: BookContact
    private let trades = ["Plumbing", "Electrical", "HVAC", "Carpentry", "Painting", "Flooring", "Roofing", "Masonry", "Tile", "Drywall", "Demolition", "General"]
    private var picked: Set<String> { Set(c.skills.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }) }
    private func toggle(_ t: String) { var s = picked; if s.contains(t) { s.remove(t) } else { s.insert(t) }; c.skills = trades.filter { s.contains($0) }.joined(separator: ", ") }

    var body: some View {
        NavigationStack {
            Form {
                Section { TextField("Name", text: $c.name); TextField("Company", text: $c.company)
                    TextField("Phone", text: $c.phone).keyboardType(.phonePad); TextField("Email", text: $c.email).keyboardType(.emailAddress).textInputAutocapitalization(.never) }
                Section("Skills") {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 100), spacing: 8)], spacing: 8) {
                        ForEach(trades, id: \.self) { t in
                            Button { toggle(t) } label: {
                                Text(t).font(.subheadline.weight(.bold)).frame(maxWidth: .infinity, minHeight: 36)
                                    .background(picked.contains(t) ? Theme.gold : Color.secondary.opacity(0.15), in: RoundedRectangle(cornerRadius: 9))
                                    .foregroundStyle(picked.contains(t) ? .black : .primary)
                            }.buttonStyle(.plain)
                        }
                    }
                }
                Section("Would you hire again?") {
                    HStack(spacing: 14) {
                        Button { c.rating = c.rating == 1 ? 0 : 1 } label: { Image(systemName: "hand.thumbsup.fill").font(.title).frame(maxWidth: .infinity, minHeight: 48)
                            .background(c.rating == 1 ? Theme.green.opacity(0.25) : Color.secondary.opacity(0.12), in: RoundedRectangle(cornerRadius: 10)).foregroundStyle(Theme.green) }.buttonStyle(.plain)
                        Button { c.rating = c.rating == -1 ? 0 : -1 } label: { Image(systemName: "hand.thumbsdown.fill").font(.title).frame(maxWidth: .infinity, minHeight: 48)
                            .background(c.rating == -1 ? Theme.red.opacity(0.25) : Color.secondary.opacity(0.12), in: RoundedRectangle(cornerRadius: 10)).foregroundStyle(Theme.red) }.buttonStyle(.plain)
                    }
                }
                Section("Notes") { TextField("Notes", text: $c.notes, axis: .vertical).lineLimit(2...6) }
            }
            .navigationTitle(c.name.isEmpty ? "New contractor" : c.name).navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }
}
