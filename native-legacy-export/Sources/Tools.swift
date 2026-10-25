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
    @Environment(\.openURL) private var openURL
    @State private var noMeasure = false
    var body: some View {
        List {
            #if os(iOS)
            NavigationLink { ARMeasureView() } label: { row("ruler", "AR Measure", "Point the camera, tap two points", Theme.sky) }
            Button {
                if let u = URL(string: "measure://") { openURL(u) { ok in if !ok { noMeasure = true } } }
            } label: { row("arrow.up.forward.app", "Apple Measure", "Open Apple's own Measure app", Theme.blue) }.buttonStyle(.plain)
            NavigationLink { LevelView() } label: { row("level", "Level", "Bubble level in degrees and in/ft", Theme.green) }
            NavigationLink { ColorMatchView() } label: { row("eyedropper", "Color match", "Sample a wall color with the camera", Theme.orange) }
            #endif
            NavigationLink { SavedResultsView() } label: { row("tray.full", "Saved results", "Everything you saved from the tools", Theme.blue) }
            NavigationLink { ContractorBookView() } label: { row("person.2.crop.square.stack", "Contractors", "Address book with skills and thumbs", Theme.gold) }
        }
        .navigationTitle("Tools")
        .alert("Apple Measure isn't available", isPresented: $noMeasure) { Button("OK", role: .cancel) {} } message: { Text("Install Measure from the App Store, or use AR Measure here.") }
    }
    private func row(_ symbol: String, _ title: String, _ sub: String, _ c: Color) -> some View {
        HStack(spacing: 14) {
            Image(systemName: symbol).font(.title2).foregroundStyle(c).frame(width: 36)
            VStack(alignment: .leading, spacing: 2) { Text(title).font(.headline); Text(sub).font(.callout).foregroundStyle(.secondary) }
        }.padding(.vertical, 4)
    }
}

extension View {
    /// Keeps the bottom of a pushed Tools screen clear of the floating back / ••• / mic buttons.
    func clearFloatBar() -> some View {
        safeAreaInset(edge: .bottom, spacing: 0) { Color.clear.frame(height: Theme.desk ? 0 : 84) }
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
    @State private var undoTick = 0
    @State private var clearTick = 0
    @State private var addTick = 0
    @State private var zoom: CGFloat = 1
    @State private var pinch: CGFloat = 1
    private var z: CGFloat { min(max(zoom * pinch, 1), 6) }
    private var total: Double { segments.reduce(0, +) }

    var body: some View {
        ZStack(alignment: .bottom) {
            if ARWorldTrackingConfiguration.isSupported {
                // Digital zoom: the picture is magnified about the screen center, and the crosshair is the screen
                // center, so the point you aim at stays exact while you see it bigger.
                // The ring is drawn ON the AR view (same frame), so it sits exactly where the raycast is aimed.
                ARMeasureRep(segments: $segments, status: $status, undoTick: undoTick, clearTick: clearTick, addTick: addTick)
                    .scaleEffect(z).clipped()
                    .overlay {
                        ZStack {
                            Circle().stroke(.white, lineWidth: 2).frame(width: 52, height: 52)
                            Circle().fill(.white).frame(width: 7, height: 7)
                        }.shadow(radius: 3).allowsHitTesting(false)
                    }
                    .ignoresSafeArea()
                    .gesture(MagnifyGesture().onChanged { pinch = $0.magnification }.onEnded { zoom = min(max(zoom * $0.magnification, 1), 6); pinch = 1 })
            } else {
                Text("AR isn't supported on this device.").foregroundStyle(.secondary).frame(maxHeight: .infinity)
            }
            VStack(spacing: 10) {
                Text(status).font(.footnote.weight(.semibold)).padding(.horizontal, 12).padding(.vertical, 6).background(.ultraThinMaterial, in: Capsule())
                HStack(spacing: 8) {
                    Image(systemName: "plus.magnifyingglass").foregroundStyle(.secondary)
                    ForEach([1, 2, 3, 4], id: \.self) { n in
                        Button { withAnimation { zoom = CGFloat(n); pinch = 1 } } label: {
                            Text("\(n)×").font(.subheadline.weight(.heavy)).frame(width: 46, height: 34)
                                .background(abs(z - CGFloat(n)) < 0.15 ? Theme.sky : Color.secondary.opacity(0.2), in: Capsule())
                                .foregroundStyle(abs(z - CGFloat(n)) < 0.15 ? .black : .primary)
                        }.buttonStyle(.plain)
                    }
                    Text(String(format: "%.1f×", Double(z))).font(.caption.weight(.bold)).foregroundStyle(.secondary)
                }
                if let last = segments.last {
                    VStack(spacing: 2) {
                        Text(feetInches(last)).font(.system(size: 34, weight: .heavy, design: .rounded))
                        if segments.count > 1 { Text("Total " + feetInches(total)).font(.callout).foregroundStyle(.secondary) }
                    }
                }
                Button { addTick += 1 } label: {
                    Image(systemName: "plus").font(.system(size: 28, weight: .semibold)).foregroundStyle(.black)
                        .frame(width: 66, height: 66).background(.white, in: Circle()).overlay(Circle().stroke(.black.opacity(0.15), lineWidth: 3))
                }
                if !segments.isEmpty {
                    SaveResultButton(tool: "AR Measure", title: segments.count > 1 ? "Total " + feetInches(total) : feetInches(segments[0]),
                                     summary: segments.enumerated().map { "Line \($0.offset + 1): " + feetInches($0.element) }.joined(separator: "\n") + (segments.count > 1 ? "\nTotal: " + feetInches(total) : ""))
                }
                HStack(spacing: 10) {
                    Button { undoTick += 1 } label: { Label("Undo", systemImage: "arrow.uturn.backward").frame(maxWidth: .infinity) }
                    Button(role: .destructive) { clearTick += 1; segments = [] } label: { Label("Clear", systemImage: "trash").frame(maxWidth: .infinity) }
                }.buttonStyle(.borderedProminent).controlSize(.large)
            }
            .padding(14).background(.bar)
        }
        .navigationTitle("AR Measure").navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .topBarTrailing) { NavigationLink { SavedResultsView(tool: "AR Measure") } label: { Image(systemName: "tray.full") } } }
        .clearFloatBar()
    }
}

struct ARMeasureRep: UIViewRepresentable {
    @Binding var segments: [Double]
    @Binding var status: String
    var undoTick: Int, clearTick: Int, addTick: Int

    func makeCoordinator() -> Coord { Coord(self) }
    func makeUIView(context: Context) -> ARSCNView {
        let v = ARSCNView()
        v.automaticallyUpdatesLighting = true
        v.session.delegate = context.coordinator
        v.delegate = context.coordinator
        let cfg = ARWorldTrackingConfiguration(); cfg.planeDetection = [.horizontal, .vertical]
        if ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh) { cfg.sceneReconstruction = .mesh }
        v.session.run(cfg)
        context.coordinator.view = v
        return v
    }
    func updateUIView(_ v: ARSCNView, context: Context) {
        let c = context.coordinator; c.parent = self
        if undoTick != c.lastUndo { c.lastUndo = undoTick; DispatchQueue.main.async { c.undo() } }
        if addTick != c.lastAdd { c.lastAdd = addTick; DispatchQueue.main.async { c.addPoint() } }
        if clearTick != c.lastClear { c.lastClear = clearTick; DispatchQueue.main.async { c.clear() } }
    }
    static func dismantleUIView(_ v: ARSCNView, coordinator: Coord) { v.session.pause() }

    /// Every point is an ARAnchor, so ARKit keeps it pinned to the real corner while its tracking improves
    /// (plain scene nodes drift). The lines and labels are re-drawn every frame between the anchors.
    final class Coord: NSObject, ARSessionDelegate, ARSCNViewDelegate {
        var parent: ARMeasureRep
        weak var view: ARSCNView?
        var lastUndo = 0, lastClear = 0, lastAdd = 0
        private let lock = NSLock()
        private var anchors: [ARAnchor] = []
        private var segs: [(line: SCNNode, label: SCNNode)] = []
        private var lastPublished: [Double] = []
        init(_ p: ARMeasureRep) { parent = p }

        func session(_ session: ARSession, didUpdate frame: ARFrame) {
            if case .normal = frame.camera.trackingState { if parent.status.hasPrefix("Move") { DispatchQueue.main.async { self.parent.status = "Aim at a corner and tap + to drop a point" } } }
        }

        // the yellow dot for each anchor
        func renderer(_ renderer: SCNSceneRenderer, nodeFor anchor: ARAnchor) -> SCNNode? {
            guard anchor.name == "pt" else { return nil }
            let dot = SCNNode(geometry: SCNSphere(radius: 0.005)); dot.geometry?.firstMaterial?.diffuse.contents = UIColor.systemYellow
            dot.geometry?.firstMaterial?.writesToDepthBuffer = false; dot.renderingOrder = 10
            return dot
        }

        // every frame: stretch each line/label between its two (anchored) dots and publish the lengths
        func renderer(_ renderer: SCNSceneRenderer, updateAtTime time: TimeInterval) {
            guard let v = view else { return }
            lock.lock(); let a = anchors, sg = segs; lock.unlock()
            var lengths: [Double] = []
            for (i, s) in sg.enumerated() {
                guard i + 1 < a.count, let n1 = v.node(for: a[i]), let n2 = v.node(for: a[i + 1]) else { lengths.append(lastPublished.indices.contains(i) ? lastPublished[i] : 0); continue }
                let p1 = n1.worldPosition, p2 = n2.worldPosition
                let d = distance(p1, p2)
                lengths.append(Double(d))
                if let cyl = s.line.geometry as? SCNCylinder { cyl.height = CGFloat(d) }
                s.line.position = SCNVector3((p1.x + p2.x) / 2, (p1.y + p2.y) / 2, (p1.z + p2.z) / 2)
                s.line.look(at: p2, up: SCNVector3(0, 1, 0), localFront: SCNVector3(0, 1, 0))
                if let t = s.label.geometry as? SCNText {
                    let str = feetInches(Double(d))
                    if (t.string as? String) != str { t.string = str; let (mn, mx) = t.boundingBox; s.label.pivot = SCNMatrix4MakeTranslation((mx.x - mn.x) / 2, 0, 0) }
                }
                s.label.position = SCNVector3((p1.x + p2.x) / 2, (p1.y + p2.y) / 2 + 0.02, (p1.z + p2.z) / 2)
            }
            if lengths.count != lastPublished.count || zip(lengths, lastPublished).contains(where: { abs($0 - $1) > 0.001 }) {
                lastPublished = lengths
                DispatchQueue.main.async { self.parent.segments = lengths }
            }
        }

        func addPoint() {
            guard let v = view else { return }
            let pt = CGPoint(x: v.bounds.midX, y: v.bounds.midY)   // the ring is always the center
            var found: ARRaycastResult?
            for target in [ARRaycastQuery.Target.existingPlaneGeometry, .existingPlaneInfinite, .estimatedPlane] {
                if let q = v.raycastQuery(from: pt, allowing: target, alignment: .any), let r = v.session.raycast(q).first { found = r; break }
            }
            guard let hit = found else { parent.status = "No surface found — move closer or add light"; return }
            let anchor = ARAnchor(name: "pt", transform: hit.worldTransform)
            v.session.add(anchor: anchor)
            lock.lock()
            if let prev = anchors.last { _ = prev
                let cyl = SCNCylinder(radius: 0.0015, height: 0.01); cyl.firstMaterial?.diffuse.contents = UIColor.systemYellow
                let line = SCNNode(geometry: cyl)
                let t = SCNText(string: "", extrusionDepth: 0.1); t.font = .boldSystemFont(ofSize: 10); t.firstMaterial?.diffuse.contents = UIColor.white
                let lab = SCNNode(geometry: t); lab.scale = SCNVector3(0.004, 0.004, 0.004); lab.constraints = [SCNBillboardConstraint()]
                v.scene.rootNode.addChildNode(line); v.scene.rootNode.addChildNode(lab)
                segs.append((line, lab))
            }
            anchors.append(anchor)
            lock.unlock()
            parent.status = "Locked. Move to the next point and tap +, or Undo / Clear"
        }
        func undo() {
            guard let v = view else { return }
            lock.lock()
            if let a = anchors.popLast() { v.session.remove(anchor: a) }
            if let s = segs.popLast() { s.line.removeFromParentNode(); s.label.removeFromParentNode() }
            lock.unlock()
        }
        func clear() {
            guard let v = view else { return }
            lock.lock()
            anchors.forEach { v.session.remove(anchor: $0) }; anchors = []
            segs.forEach { $0.line.removeFromParentNode(); $0.label.removeFromParentNode() }; segs = []
            lock.unlock()
            lastPublished = []
        }

        private func distance(_ a: SCNVector3, _ b: SCNVector3) -> Float { sqrtf((a.x-b.x)*(a.x-b.x) + (a.y-b.y)*(a.y-b.y) + (a.z-b.z)*(a.z-b.z)) }
    }
}

// MARK: - Level

final class LevelMotion: ObservableObject {
    private let mm = CMMotionManager()
    @Published var gx = 0.0
    @Published var gy = 0.0
    @Published var gz = -1.0
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
    @State private var zeroX = 0.0
    @State private var zeroY = 0.0
    @State private var zeroEdge = 0.0
    private var flat: Bool { abs(mo.gz) > 0.8 }
    private var edgeRaw: Double { atan2(mo.gx, -mo.gy) * 180 / .pi }
    private var edgeDev: Double { let r = edgeRaw - (edgeRaw / 90).rounded() * 90; return r - zeroEdge }
    private var tiltX: Double { mo.gx - zeroX }
    private var tiltY: Double { mo.gy - zeroY }
    private var deg: Double { flat ? asin(min(1, sqrt(tiltX * tiltX + tiltY * tiltY))) * 180 / .pi : abs(edgeDev) }
    private var inPerFt: Double { tan(deg * .pi / 180) * 12 }
    private var isLevel: Bool { deg < 0.3 }

    private let liquid = Color(red: 0.85, green: 0.93, blue: 0.25)
    private var accent: Color { isLevel ? Theme.green : Color(red: 0.98, green: 0.76, blue: 0.1) }

    /// Spirit-level glass: a tube (or round window) of yellow-green liquid with a bubble and two center marks.
    private func bubbleOffset(_ v: Double, limit: Double, k: Double) -> Double { max(-limit, min(limit, v * k)) }

    var body: some View {
        // Classic bubble (spirit) level: yellow body, liquid vials, bubble floats to the high side.
        ZStack {
            Color(red: 0.12, green: 0.12, blue: 0.13).ignoresSafeArea()
            VStack(spacing: 18) {
                Text(String(format: "%.1f°", deg)).font(.system(size: 64, weight: .bold, design: .rounded)).foregroundStyle(accent).monospacedDigit().padding(.top, 14)
                Text(flat ? "Phone flat — bubble goes to the high side" : "Phone on its edge").font(.callout).foregroundStyle(.white.opacity(0.7))
                ZStack {
                    RoundedRectangle(cornerRadius: 26).fill(accent)
                    if flat {
                        ZStack {   // round bullseye vial
                            Circle().fill(liquid).overlay(Circle().stroke(.black.opacity(0.55), lineWidth: 5))
                            Circle().stroke(.black.opacity(0.55), lineWidth: 2).frame(width: 70, height: 70)
                            Circle().fill(.white.opacity(0.55)).overlay(Circle().stroke(.black.opacity(0.5), lineWidth: 2)).frame(width: 54, height: 54)
                                .offset(x: bubbleOffset(-tiltX, limit: 86, k: 900), y: bubbleOffset(tiltY, limit: 86, k: 900))
                        }.frame(width: 250, height: 250)
                    } else {
                        ZStack {   // long horizontal vial
                            Capsule().fill(liquid).overlay(Capsule().stroke(.black.opacity(0.55), lineWidth: 5))
                            HStack(spacing: 64) { Rectangle().fill(.black.opacity(0.55)).frame(width: 3); Rectangle().fill(.black.opacity(0.55)).frame(width: 3) }.padding(.vertical, 8)
                            Ellipse().fill(.white.opacity(0.55)).overlay(Ellipse().stroke(.black.opacity(0.5), lineWidth: 2)).frame(width: 60, height: 34)
                                .offset(x: bubbleOffset(-edgeDev, limit: 130, k: 18))
                        }.frame(width: 320, height: 76)
                    }
                }.frame(maxWidth: 340, maxHeight: flat ? 290 : 150)
                Text(isLevel ? "LEVEL" : String(format: "%.2f in per foot", inPerFt)).font(.title3.weight(.heavy)).foregroundStyle(accent)
                Spacer(minLength: 0)
                HStack(spacing: 10) {
                    Button { zeroX = mo.gx; zeroY = mo.gy; zeroEdge = edgeRaw - (edgeRaw / 90).rounded() * 90 } label: {
                        Text("Calibrate").font(.subheadline.weight(.bold)).foregroundStyle(.black).frame(maxWidth: .infinity, minHeight: 40).background(.white, in: Capsule())
                    }
                    SaveResultButton(tool: "Level", title: String(format: "%.1f°", deg),
                                     summary: String(format: "%.1f° · %.2f in per foot · ", deg, inPerFt) + (isLevel ? "level" : "not level") + (flat ? " (flat)" : " (edge)"))
                }.padding(.horizontal, 24).padding(.bottom, 8)
            }
        }
        .navigationTitle("Level").navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .topBarTrailing) { NavigationLink { SavedResultsView(tool: "Level") } label: { Image(systemName: "tray.full") } } }
        .toolbarColorScheme(.dark, for: .navigationBar)
        .clearFloatBar()
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

    private var colorSummary: String {
        var t = "\(hex(cur))  ·  R \(Int(cur.0 * 255)) G \(Int(cur.1 * 255)) B \(Int(cur.2 * 255))" + (white != nil ? "  (white-corrected)" : "")
        if let a { t += "\nSample A: " + hex(a) }
        if let b { t += "\nSample B: " + hex(b) }
        if let a, let b { let d = delta(a, b); t += "\nA vs B: " + (d < 4 ? "very close" : d < 12 ? "close" : "visibly different") }
        return t
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
                    slot("Save A", a) { a = cur }
                    slot("Save B", b) { b = cur }
                    Button { if white == nil { white = cam.rgb } else { white = nil } } label: { Text(white == nil ? "Set white" : "Reset").font(.subheadline.weight(.bold)).frame(maxWidth: .infinity, minHeight: 44) }
                        .buttonStyle(.bordered)
                }
                SaveResultButton(tool: "Color match", title: hex(cur), summary: colorSummary)
                if let a, let b {
                    let d = delta(a, b)
                    Text(d < 4 ? "Very close match" : d < 12 ? "Close — slight difference" : "Visibly different")
                        .font(.headline).foregroundStyle(d < 4 ? Theme.green : d < 12 ? Theme.orange : Theme.red)
                }
                Text("Tip: point at white paper first and tap Set white — it cancels out room lighting.").font(.caption).foregroundStyle(.secondary)
            }.padding(14).background(.bar)
        }
        .navigationTitle("Color match").navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .topBarTrailing) { NavigationLink { SavedResultsView(tool: "Color match") } label: { Image(systemName: "tray.full") } } }
        .clearFloatBar()
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
        .clearFloatBar()
        .onAppear { all.filter { $0.name.trimmingCharacters(in: .whitespaces).isEmpty && $0.company.isEmpty && $0.phone.isEmpty && $0.skills.isEmpty }.forEach { context.delete($0) } }
        .toolbar { ToolbarItem(placement: .primaryAction) { Button { let c = BookContact(name: ""); context.insert(c); editing = c } label: { Image(systemName: "plus") } } }
        .sheet(item: $editing) { c in ContractorEditor(c: c) }
    }
}

struct ContractorEditor: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @Bindable var c: BookContact
    private let trades = ["Plumbing", "Electrical", "HVAC", "Carpentry", "Painting", "Flooring", "Roofing", "Masonry", "Tile", "Drywall", "Demolition", "General"]
    private var picked: Set<String> { Set(c.skills.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }) }
    private func toggle(_ t: String) { var s = picked; if s.contains(t) { s.remove(t) } else { s.insert(t) }; c.skills = trades.filter { s.contains($0) }.joined(separator: ", ") }

    var body: some View {
        NavigationStack {
            Form {
                Section { TextField("Name", text: $c.name); TextField("Company", text: $c.company)
                    TextField("Phone", text: $c.phone); TextField("Email", text: $c.email) }
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
            .navigationTitle(c.name.isEmpty ? "New contractor" : c.name)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
        .onDisappear { if c.name.trimmingCharacters(in: .whitespaces).isEmpty && c.company.isEmpty && c.phone.isEmpty && c.skills.isEmpty { context.delete(c) } }
    }
}


// MARK: - Saved results (all tools)

@Model
final class ToolResult {
    var tool: String = ""          // "AR Measure", "Level", "Color match"
    var title: String = ""         // headline, e.g. "12′ 4″"
    var summary: String = ""       // the full readout
    var note: String = ""
    var jobName: String = ""
    var created: Date = Date()
    init(tool: String, title: String, summary: String) { self.tool = tool; self.title = title; self.summary = summary }
}

struct SaveResultSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    @Query(sort: \Job.created, order: .reverse) private var jobs: [Job]
    @AppStorage("bpActiveJob") private var activeKey = ""
    let tool: String, title: String, summary: String
    @State private var jobID: PersistentIdentifier?
    @State private var label = ""
    @State private var note = ""
    var body: some View {
        NavigationStack {
            Form {
                Section(tool) { Text(title).font(.title2.weight(.heavy)); Text(summary).font(.callout).foregroundStyle(.secondary) }
                Section {
                    TextField("Label (e.g. Kitchen wall)", text: $label)
                    TextField("Note", text: $note, axis: .vertical)
                    Picker("Job", selection: $jobID) {
                        Text("No job").tag(PersistentIdentifier?.none)
                        ForEach(jobs.filter { $0.isActive }) { j in Text(j.name.isEmpty ? "Job" : j.name).tag(Optional(j.persistentModelID)) }
                    }
                }
            }
            .navigationTitle("Save result")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) { Button("Save") { save() }.bold() }
            }
            .onAppear { if jobID == nil { jobID = jobs.first { String($0.created.timeIntervalSince1970) == activeKey }?.persistentModelID } }
        }
        .presentationDetents([.medium, .large])
    }
    private func save() {
        let job = jobs.first { $0.persistentModelID == jobID }
        let head = label.isEmpty ? title : label + " — " + title
        let r = ToolResult(tool: tool, title: head, summary: summary)
        r.note = note; r.jobName = job?.name ?? ""
        context.insert(r)
        if let job {   // also show it in the job's Notes
            let n = JobNote(title: tool + ": " + head)
            n.text = summary + (note.isEmpty ? "" : "\n" + note); n.job = job
            context.insert(n)
        }
        try? context.save()
        dismiss()
    }
}

/// Green "Save" button used by every tool.
struct SaveResultButton: View {
    let tool: String, title: String, summary: String
    @State private var show = false
    var body: some View {
        Button { show = true } label: { Label("Save", systemImage: "square.and.arrow.down").font(.subheadline.weight(.bold)).frame(maxWidth: .infinity, minHeight: 40) }
            .buttonStyle(.borderedProminent).tint(Theme.green).foregroundStyle(.black)
            .sheet(isPresented: $show) { SaveResultSheet(tool: tool, title: title, summary: summary) }
    }
}

struct SavedResultsView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \ToolResult.created, order: .reverse) private var all: [ToolResult]
    var tool: String? = nil
    private var items: [ToolResult] { tool == nil ? all : all.filter { $0.tool == tool } }
    var body: some View {
        List {
            if items.isEmpty { Text("Nothing saved yet. Use Save on a tool.").foregroundStyle(.secondary) }
            ForEach(items) { r in
                VStack(alignment: .leading, spacing: 3) {
                    HStack { Text(r.title).font(.headline); Spacer(); Text(r.tool).font(.caption.weight(.bold)).foregroundStyle(.secondary) }
                    Text(r.summary).font(.callout).foregroundStyle(.secondary)
                    if !r.note.isEmpty { Text(r.note).font(.callout) }
                    Text((r.jobName.isEmpty ? "" : r.jobName + " · ") + r.created.formatted(date: .abbreviated, time: .shortened)).font(.caption).foregroundStyle(.secondary)
                }.padding(.vertical, 2)
            }
            .onDelete { idx in idx.forEach { context.delete(items[$0]) } }
        }
        .navigationTitle(tool.map { $0 + " — saved" } ?? "Saved results")
        .clearFloatBar()
    }
}
