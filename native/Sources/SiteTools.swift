import Foundation
import WebKit
#if os(iOS)
import UIKit
import ARKit
import RealityKit
import Combine
#if canImport(RoomPlan)
import RoomPlan
#endif
#endif

/// v6.2.7 — Apple's site tools inside BuildersPro (iPhone / iPad only):
///  • Measure  — LiDAR / AR tape: aim the dot, tap +, tap + again. Feet-inches to 1/8".
///  • Room scan — RoomPlan: walk the room, get a floor plan with wall lengths, area and ceiling height,
///                 plus a 3D model file (USDZ) saved in Files › BuildersPro › Room Scans.
/// The page asks with { kind: 'measure' } or { kind: 'roomScan' }; the answer comes back through
/// window.bpNativeDone({ tool, ok, image, ... }). The Mac has neither (no camera tracking), so it says so.
enum SiteTools {

    /// What this device can do — handed to the page as window.BPShell.caps.
    static func capsJS() -> String {
        #if os(iOS)
        let ar = ARWorldTrackingConfiguration.isSupported
        let lidar = ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh)
        var room = false
        #if canImport(RoomPlan)
        room = RoomCaptureSession.isSupported
        #endif
        return "{measure:\(ar),lidar:\(lidar),roomScan:\(room),ai:true,drive:true}"
        #else
        return "{measure:false,lidar:false,roomScan:false,ai:true,drive:true}"
        #endif
    }

    /// Feet and inches to the nearest 1/8".
    static func feetInches(_ meters: Float) -> String {
        let eighths = Int((Double(meters) * 39.37007874 * 8).rounded())
        let ft = eighths / 96, rem = eighths % 96, inch = rem / 8, e = rem % 8
        let fr = ["", " 1/8", " 1/4", " 3/8", " 1/2", " 5/8", " 3/4", " 7/8"][e]
        return ft > 0 ? "\(ft)' \(inch)\(fr)\"" : "\(inch)\(fr)\""
    }

    static func json(_ obj: [String: Any]) -> String {
        guard let d = try? JSONSerialization.data(withJSONObject: obj),
              let s = String(data: d, encoding: .utf8) else { return "{ok:false}" }
        return s
    }

    /// Where room-scan 3D files go: iCloud Drive › BuildersPro › Room Scans, else Files › On My iPhone › BuildersPro.
    static func scanFolder() -> URL? {
        let fm = FileManager.default
        if let c = fm.url(forUbiquityContainerIdentifier: DailyBackup.containerID) {
            let d = c.appendingPathComponent("Documents/Room Scans", isDirectory: true)
            if (try? fm.createDirectory(at: d, withIntermediateDirectories: true)) != nil { return d }
        }
        if let docs = fm.urls(for: .documentDirectory, in: .userDomainMask).first {
            let d = docs.appendingPathComponent("Room Scans", isDirectory: true)
            if (try? fm.createDirectory(at: d, withIntermediateDirectories: true)) != nil { return d }
        }
        return nil
    }
}

extension ShellModel {
    func siteTool(_ kind: String, _ body: [String: Any]) {
        let reply: ([String: Any]) -> Void = { [weak self] obj in
            self?.webView.evaluateJavaScript("window.bpNativeDone && window.bpNativeDone(" + SiteTools.json(obj) + ")")
        }
        #if os(iOS)
        guard let top = topViewController() else { return }
        switch kind {
        case "measure":
            guard ARWorldTrackingConfiguration.isSupported else {
                reply(["tool": "measure", "ok": false, "err": "This device can't measure with AR."]); return
            }
            let vc = MeasureVC()
            vc.onDone = { reply($0 ?? ["tool": "measure", "ok": false, "cancel": true]) }
            vc.modalPresentationStyle = .fullScreen
            top.present(vc, animated: true)
        case "roomScan":
            #if canImport(RoomPlan)
            guard RoomCaptureSession.isSupported else {
                reply(["tool": "room", "ok": false, "err": "Room scan needs an iPhone Pro or iPad Pro with LiDAR."]); return
            }
            let vc = RoomScanVC()
            vc.onDone = { reply($0 ?? ["tool": "room", "ok": false, "cancel": true]) }
            vc.modalPresentationStyle = .fullScreen
            top.present(vc, animated: true)
            #else
            reply(["tool": "room", "ok": false, "err": "Room scan is not available on this device."])
            #endif
        case "roomShare3D":
            let name = (body["name"] as? String) ?? ""
            guard !name.isEmpty, !name.contains("/"), let dir = SiteTools.scanFolder() else { return }
            let url = dir.appendingPathComponent(name)
            guard FileManager.default.fileExists(atPath: url.path) else {
                reply(["tool": "share3d", "ok": false, "err": "The 3D file is on the device that scanned the room."]); return
            }
            let sheet = UIActivityViewController(activityItems: [url], applicationActivities: nil)
            if let pop = sheet.popoverPresentationController {
                pop.sourceView = webView
                pop.sourceRect = CGRect(x: webView.bounds.midX, y: webView.bounds.midY, width: 1, height: 1)
                pop.permittedArrowDirections = []
            }
            top.present(sheet, animated: true)
        default: break
        }
        #else
        reply(["tool": kind == "roomScan" ? "room" : "measure", "ok": false,
               "err": "Measure and Room scan run on iPhone or iPad. Results show here once they sync."])
        #endif
    }
}

#if os(iOS)

// MARK: - Shared look

private enum Look {
    static let blue = UIColor(red: 10/255, green: 132/255, blue: 1, alpha: 1)
    static let green = UIColor(red: 48/255, green: 209/255, blue: 88/255, alpha: 1)

    static func round(_ symbol: String, _ label: String, size: CGFloat = 52, fill: UIColor = UIColor.black.withAlphaComponent(0.55)) -> UIButton {
        let b = UIButton(type: .system)
        b.setImage(UIImage(systemName: symbol, withConfiguration: UIImage.SymbolConfiguration(pointSize: size * 0.4, weight: .semibold)), for: .normal)
        b.tintColor = .white
        b.backgroundColor = fill
        b.layer.cornerRadius = size / 2
        b.accessibilityLabel = label
        b.translatesAutoresizingMaskIntoConstraints = false
        b.widthAnchor.constraint(equalToConstant: size).isActive = true
        b.heightAnchor.constraint(equalToConstant: size).isActive = true
        return b
    }

    static func pill(_ title: String, _ color: UIColor) -> UIButton {
        var c = UIButton.Configuration.filled()
        c.title = title
        c.baseBackgroundColor = color
        c.baseForegroundColor = .white
        c.cornerStyle = .capsule
        c.contentInsets = NSDirectionalEdgeInsets(top: 0, leading: 22, bottom: 0, trailing: 22)
        c.titleTextAttributesTransformer = UIConfigurationTextAttributesTransformer { a in
            var a = a; a.font = .systemFont(ofSize: 18, weight: .heavy); return a
        }
        let b = UIButton(configuration: c)
        b.translatesAutoresizingMaskIntoConstraints = false
        b.heightAnchor.constraint(equalToConstant: 52).isActive = true
        return b
    }

    static func hint() -> UILabel {
        let l = UILabel()
        l.font = .systemFont(ofSize: 17, weight: .bold)
        l.textColor = .white
        l.textAlignment = .center
        l.numberOfLines = 2
        l.backgroundColor = UIColor.black.withAlphaComponent(0.55)
        l.layer.cornerRadius = 12
        l.clipsToBounds = true
        l.translatesAutoresizingMaskIntoConstraints = false
        return l
    }
}

// MARK: - Measure (ARKit / LiDAR tape)

final class MeasureVC: UIViewController {
    var onDone: (([String: Any]?) -> Void)?

    private let arView = ARView(frame: .zero, cameraMode: .ar, automaticallyConfigureSession: false)
    private let root = AnchorEntity(world: .zero)
    private var segments: [(SIMD3<Float>, SIMD3<Float>)] = []
    private var start: SIMD3<Float>?
    private var aim: SIMD3<Float>?
    private var liveLine: ModelEntity?
    private var labels: [UILabel] = []
    private let liveLabel = UILabel()
    private let reticle = UIView()
    private let hint = Look.hint()
    private var sub: Cancellable?
    private var finished = false

    override var prefersStatusBarHidden: Bool { true }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        arView.frame = view.bounds
        arView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(arView)
        arView.scene.addAnchor(root)

        let coach = ARCoachingOverlayView()
        coach.session = arView.session
        coach.goal = .tracking
        coach.activatesAutomatically = true
        coach.frame = view.bounds
        coach.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        arView.addSubview(coach)

        reticle.frame = CGRect(x: 0, y: 0, width: 34, height: 34)
        reticle.layer.cornerRadius = 17
        reticle.layer.borderWidth = 3
        reticle.layer.borderColor = UIColor.white.cgColor
        reticle.isUserInteractionEnabled = false
        let dot = UIView(frame: CGRect(x: 14, y: 14, width: 6, height: 6))
        dot.backgroundColor = .white; dot.layer.cornerRadius = 3
        reticle.addSubview(dot)
        view.addSubview(reticle)

        styleTag(liveLabel); liveLabel.isHidden = true
        view.addSubview(liveLabel)

        let close = Look.round("xmark", "Close")
        close.addTarget(self, action: #selector(cancel), for: .touchUpInside)
        let undo = Look.round("arrow.uturn.backward", "Undo")
        undo.addTarget(self, action: #selector(undoTap), for: .touchUpInside)
        let add = Look.round("plus", "Add point", size: 78, fill: .white)
        add.tintColor = .black
        add.addTarget(self, action: #selector(addTap), for: .touchUpInside)
        let save = Look.pill("Save", Look.blue)
        save.addTarget(self, action: #selector(saveTap), for: .touchUpInside)

        hint.text = "Aim the dot at the first spot, then tap +"
        for v in [close, undo, add, save, hint] as [UIView] { view.addSubview(v) }
        let g = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            close.leadingAnchor.constraint(equalTo: g.leadingAnchor, constant: 16),
            close.topAnchor.constraint(equalTo: g.topAnchor, constant: 10),
            undo.trailingAnchor.constraint(equalTo: g.trailingAnchor, constant: -16),
            undo.topAnchor.constraint(equalTo: g.topAnchor, constant: 10),
            hint.topAnchor.constraint(equalTo: close.bottomAnchor, constant: 12),
            hint.centerXAnchor.constraint(equalTo: g.centerXAnchor),
            hint.widthAnchor.constraint(lessThanOrEqualTo: g.widthAnchor, constant: -32),
            hint.heightAnchor.constraint(greaterThanOrEqualToConstant: 44),
            add.centerXAnchor.constraint(equalTo: g.centerXAnchor),
            add.bottomAnchor.constraint(equalTo: g.bottomAnchor, constant: -24),
            save.centerYAnchor.constraint(equalTo: add.centerYAnchor),
            save.trailingAnchor.constraint(equalTo: g.trailingAnchor, constant: -16),
        ])

        sub = arView.scene.subscribe(to: SceneEvents.Update.self) { [weak self] _ in self?.frame() }
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        reticle.center = CGPoint(x: view.bounds.midX, y: view.bounds.midY)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        let cfg = ARWorldTrackingConfiguration()
        cfg.planeDetection = [.horizontal, .vertical]
        if ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh) { cfg.sceneReconstruction = .mesh }
        arView.session.run(cfg)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        arView.session.pause()
        sub?.cancel()
    }

    private func styleTag(_ l: UILabel) {
        l.font = .monospacedDigitSystemFont(ofSize: 20, weight: .heavy)
        l.textColor = .black
        l.backgroundColor = .white
        l.textAlignment = .center
        l.layer.cornerRadius = 10
        l.clipsToBounds = true
    }

    private func place(_ l: UILabel, at world: SIMD3<Float>) {
        guard let p = arView.project(world) else { l.isHidden = true; return }
        l.sizeToFit()
        l.frame.size = CGSize(width: l.frame.width + 18, height: 34)
        l.center = p
        l.isHidden = false
    }

    private func frame() {
        let c = CGPoint(x: arView.bounds.midX, y: arView.bounds.midY)
        if let hit = arView.raycast(from: c, allowing: .estimatedPlane, alignment: .any).first {
            let t = hit.worldTransform.columns.3
            aim = SIMD3(t.x, t.y, t.z)
            reticle.layer.borderColor = UIColor.white.cgColor
        } else {
            aim = nil
            reticle.layer.borderColor = UIColor.white.withAlphaComponent(0.35).cgColor
        }
        if let s = start, let a = aim {
            setLine(&liveLine, s, a, color: .white)
            liveLabel.text = SiteTools.feetInches(simd_distance(s, a))
            place(liveLabel, at: (s + a) / 2)
        } else {
            liveLine?.isEnabled = false
            liveLabel.isHidden = true
        }
        for (i, seg) in segments.enumerated() where i < labels.count { place(labels[i], at: (seg.0 + seg.1) / 2) }
    }

    private func setLine(_ line: inout ModelEntity?, _ a: SIMD3<Float>, _ b: SIMD3<Float>, color: UIColor) {
        let len = simd_distance(a, b)
        let mesh = MeshResource.generateBox(size: [0.004, 0.004, max(len, 0.001)])
        if line == nil {
            let e = ModelEntity(mesh: mesh, materials: [UnlitMaterial(color: color)])
            root.addChild(e); line = e
        } else {
            line?.model?.mesh = mesh
        }
        line?.isEnabled = len > 0.001
        let mid = (a + b) / 2
        if len > 0.001 { line?.look(at: b, from: mid, relativeTo: nil) }
    }

    private func dot(_ p: SIMD3<Float>) {
        let e = ModelEntity(mesh: .generateSphere(radius: 0.007), materials: [UnlitMaterial(color: .white)])
        e.position = p
        root.addChild(e)
    }

    @objc private func addTap() {
        guard let a = aim else { hint.text = "Can't find a surface there. Move slowly and aim again"; return }
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        dot(a)
        if let s = start {
            var line: ModelEntity?
            setLine(&line, s, a, color: Look.green)
            segments.append((s, a))
            let l = UILabel(); styleTag(l); l.text = SiteTools.feetInches(simd_distance(s, a))
            view.insertSubview(l, belowSubview: reticle); labels.append(l)
            start = nil
            hint.text = "\(segments.count) measured. Tap + for another, or Save"
        } else {
            start = a
            hint.text = "Now aim at the end spot and tap +"
        }
    }

    @objc private func undoTap() {
        if start != nil { start = nil; hint.text = "Aim the dot at the first spot, then tap +"; rebuild(); return }
        guard !segments.isEmpty else { return }
        segments.removeLast(); labels.removeLast().removeFromSuperview()
        rebuild()
        hint.text = segments.isEmpty ? "Aim the dot at the first spot, then tap +" : "\(segments.count) measured"
    }

    private func rebuild() {
        for c in Array(root.children) { c.removeFromParent() }
        liveLine = nil
        for s in segments { dot(s.0); dot(s.1); var l: ModelEntity?; setLine(&l, s.0, s.1, color: Look.green) }
        if let s = start { dot(s) }
    }

    @objc private func cancel() { finish(nil) }

    @objc private func saveTap() {
        guard !segments.isEmpty else { hint.text = "Measure something first: tap + at each end"; return }
        start = nil; liveLine?.isEnabled = false; liveLabel.isHidden = true
        reticle.isHidden = true
        let tags = labels.map { ($0.text ?? "", $0.center) }
        let size = arView.bounds.size
        arView.snapshot(saveToHDR: false) { [weak self] img in
            guard let self else { return }
            let lengths = self.segments.map { SiteTools.feetInches(simd_distance($0.0, $0.1)) }
            let inches = self.segments.map { Double(simd_distance($0.0, $0.1)) * 39.37007874 }
            let photo = Self.burn(img, tags: tags, viewSize: size)
            var out: [String: Any] = ["tool": "measure", "ok": true, "lengths": lengths, "inches": inches,
                                      "lidar": ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh)]
            if let d = photo?.jpegData(compressionQuality: 0.82) { out["image"] = "data:image/jpeg;base64," + d.base64EncodedString() }
            self.finish(out)
        }
    }

    /// The snapshot has the green lines but not the length tags — draw them onto the picture.
    private static func burn(_ img: UIImage?, tags: [(String, CGPoint)], viewSize: CGSize) -> UIImage? {
        guard let img else { return nil }
        let sx = img.size.width / max(viewSize.width, 1), sy = img.size.height / max(viewSize.height, 1)
        let r = UIGraphicsImageRenderer(size: img.size)
        return r.image { _ in
            img.draw(at: .zero)
            let font = UIFont.monospacedDigitSystemFont(ofSize: 22 * sx, weight: .heavy)
            for (t, p) in tags {
                let s = NSAttributedString(string: t, attributes: [.font: font, .foregroundColor: UIColor.black])
                let sz = s.size()
                let box = CGRect(x: p.x * sx - sz.width / 2 - 10 * sx, y: p.y * sy - sz.height / 2 - 6 * sy,
                                 width: sz.width + 20 * sx, height: sz.height + 12 * sy)
                UIColor.white.setFill()
                UIBezierPath(roundedRect: box, cornerRadius: 10 * sx).fill()
                s.draw(at: CGPoint(x: box.minX + 10 * sx, y: box.minY + 6 * sy))
            }
        }
    }

    private func finish(_ result: [String: Any]?) {
        guard !finished else { return }
        finished = true
        arView.session.pause()
        dismiss(animated: true) { [onDone] in onDone?(result) }
    }
}

// MARK: - Room scan (RoomPlan)

#if canImport(RoomPlan)
final class RoomScanVC: UIViewController, RoomCaptureViewDelegate {
    var onDone: (([String: Any]?) -> Void)?

    private var captureView: RoomCaptureView!
    private var room: CapturedRoom?
    private var scanning = false
    private var finished = false
    private let hint = Look.hint()
    private let doneBtn = Look.pill("Done scanning", Look.blue)
    private let saveBtn = Look.pill("Save to job", Look.green)

    override var prefersStatusBarHidden: Bool { true }

    init() { super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { super.init(coder: coder) }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        captureView = RoomCaptureView(frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        captureView.delegate = self
        view.addSubview(captureView)

        let close = Look.round("xmark", "Close")
        close.addTarget(self, action: #selector(cancel), for: .touchUpInside)
        doneBtn.addTarget(self, action: #selector(doneTap), for: .touchUpInside)
        saveBtn.addTarget(self, action: #selector(saveTap), for: .touchUpInside)
        saveBtn.isHidden = true
        hint.text = "Walk the room slowly. Point at every wall, door and window"
        for v in [close, hint, doneBtn, saveBtn] as [UIView] { view.addSubview(v) }
        let g = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            close.leadingAnchor.constraint(equalTo: g.leadingAnchor, constant: 16),
            close.topAnchor.constraint(equalTo: g.topAnchor, constant: 10),
            hint.topAnchor.constraint(equalTo: close.bottomAnchor, constant: 12),
            hint.centerXAnchor.constraint(equalTo: g.centerXAnchor),
            hint.widthAnchor.constraint(lessThanOrEqualTo: g.widthAnchor, constant: -32),
            hint.heightAnchor.constraint(greaterThanOrEqualToConstant: 44),
            doneBtn.centerXAnchor.constraint(equalTo: g.centerXAnchor),
            doneBtn.bottomAnchor.constraint(equalTo: g.bottomAnchor, constant: -24),
            saveBtn.centerXAnchor.constraint(equalTo: g.centerXAnchor),
            saveBtn.bottomAnchor.constraint(equalTo: g.bottomAnchor, constant: -24),
        ])
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        guard !scanning, room == nil else { return }
        scanning = true
        captureView.captureSession.run(configuration: RoomCaptureSession.Configuration())
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        if scanning { captureView.captureSession.stop(); scanning = false }
    }

    @objc private func doneTap() {
        guard scanning else { return }
        scanning = false
        captureView.captureSession.stop()
        doneBtn.isHidden = true
        hint.text = "Building the floor plan…"
    }

    func captureView(shouldPresent roomDataForProcessing: CapturedRoomData, error: Error?) -> Bool { true }

    func captureView(didPresent processedResult: CapturedRoom, error: Error?) {
        if let error {
            hint.text = "Scan didn't finish: \(error.localizedDescription)"
            return
        }
        room = processedResult
        hint.text = "\(processedResult.walls.count) walls found. Check it, then Save to job"
        saveBtn.isHidden = false
    }

    @objc private func cancel() { finish(nil) }

    @objc private func saveTap() {
        guard let room else { return }
        saveBtn.isEnabled = false
        hint.text = "Saving…"
        let stamp: String = {
            let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd HH.mm"; return f.string(from: Date())
        }()
        let plan = FloorPlan(room)
        var out: [String: Any] = ["tool": "room", "ok": true].merging(plan.summary) { a, _ in a }
        if let img = plan.render(title: "Room scan · " + stamp), let d = img.jpegData(compressionQuality: 0.88) {
            out["image"] = "data:image/jpeg;base64," + d.base64EncodedString()
        }
        let name = "Room scan \(stamp).usdz"
        if let dir = SiteTools.scanFolder() {
            let url = dir.appendingPathComponent(name)
            try? FileManager.default.removeItem(at: url)
            if (try? room.export(to: url)) != nil { out["usdz"] = name }
        }
        finish(out)
    }

    private func finish(_ result: [String: Any]?) {
        guard !finished else { return }
        finished = true
        if scanning { captureView.captureSession.stop(); scanning = false }
        dismiss(animated: true) { [onDone] in onDone?(result) }
    }
}

/// Turns a RoomPlan result into numbers and a top-down drawing with every wall's length.
private struct FloorPlan {
    struct Seg { let a: CGPoint; let b: CGPoint; let len: Float }
    var walls: [Seg] = [], doors: [Seg] = [], windows: [Seg] = [], openings: [Seg] = []
    var ceiling: Float = 0
    var area: Float = 0

    init(_ room: CapturedRoom) {
        func seg(_ s: CapturedRoom.Surface) -> Seg {
            let half = s.dimensions.x / 2
            let p = s.transform * SIMD4<Float>(-half, 0, 0, 1), q = s.transform * SIMD4<Float>(half, 0, 0, 1)
            return Seg(a: CGPoint(x: CGFloat(p.x), y: CGFloat(p.z)), b: CGPoint(x: CGFloat(q.x), y: CGFloat(q.z)), len: s.dimensions.x)
        }
        walls = room.walls.map(seg)
        doors = room.doors.map(seg)
        windows = room.windows.map(seg)
        openings = room.openings.map(seg)
        ceiling = room.walls.map { $0.dimensions.y }.max() ?? 0
        area = room.floors.map(FloorPlan.floorArea).reduce(0, +)
    }

    /// Floor area from the floor's outline; falls back to its bounding box.
    static func floorArea(_ f: CapturedRoom.Surface) -> Float {
        let c = f.polygonCorners
        if c.count >= 3 {
            // the outline lies flat in two of the three axes — use the two that vary most
            func spread(_ k: Int) -> Float { let v = c.map { $0[k] }; return (v.max() ?? 0) - (v.min() ?? 0) }
            let axes = [0, 1, 2].sorted { spread($0) > spread($1) }
            let i = axes[0], j = axes[1]
            var s: Float = 0
            for n in 0..<c.count { let a = c[n], b = c[(n + 1) % c.count]; s += a[i] * b[j] - b[i] * a[j] }
            return abs(s) / 2
        }
        return f.dimensions.x * f.dimensions.y
    }

    var summary: [String: Any] {
        let sqft = Double(area) * 10.7639104
        let perim = walls.reduce(Float(0)) { $0 + $1.len }
        return [
            "walls": walls.map { SiteTools.feetInches($0.len) },
            "wallCount": walls.count,
            "doors": doors.count, "windows": windows.count, "openings": openings.count,
            "areaSqFt": (sqft * 10).rounded() / 10,
            "perimeter": SiteTools.feetInches(perim),
            "perimeterFt": (Double(perim) * 3.2808399 * 10).rounded() / 10,
            "ceiling": ceiling > 0 ? SiteTools.feetInches(ceiling) : "",
        ]
    }

    func render(title: String) -> UIImage? {
        let pts = (walls + doors + windows + openings).flatMap { [$0.a, $0.b] }
        guard !pts.isEmpty else { return nil }
        let W: CGFloat = 1600, H: CGFloat = 1800, pad: CGFloat = 170, head: CGFloat = 200
        let minX = pts.map(\.x).min()!, maxX = pts.map(\.x).max()!
        let minY = pts.map(\.y).min()!, maxY = pts.map(\.y).max()!
        let k = min((W - pad * 2) / max(maxX - minX, 0.1), (H - head - pad * 2) / max(maxY - minY, 0.1))
        let ox = (W - (maxX - minX) * k) / 2, oy = head + (H - head - (maxY - minY) * k) / 2
        func P(_ p: CGPoint) -> CGPoint { CGPoint(x: ox + (p.x - minX) * k, y: oy + (p.y - minY) * k) }
        let mid = CGPoint(x: pts.map(\.x).reduce(0, +) / CGFloat(pts.count), y: pts.map(\.y).reduce(0, +) / CGFloat(pts.count))

        return UIGraphicsImageRenderer(size: CGSize(width: W, height: H)).image { ctx in
            let g = ctx.cgContext
            UIColor.white.setFill(); g.fill(CGRect(x: 0, y: 0, width: W, height: H))
            g.setLineCap(.round)

            func line(_ s: Seg, _ color: UIColor, _ w: CGFloat) {
                g.setStrokeColor(color.cgColor); g.setLineWidth(w)
                g.move(to: P(s.a)); g.addLine(to: P(s.b)); g.strokePath()
            }
            walls.forEach { line($0, UIColor(white: 0.12, alpha: 1), 16) }
            openings.forEach { line($0, .white, 18) }
            windows.forEach { line($0, .white, 18); line($0, UIColor(red: 0.35, green: 0.7, blue: 1, alpha: 1), 8) }
            doors.forEach { line($0, .white, 18); line($0, Look.blue, 6) }

            // wall lengths, pushed outward from the room's middle
            let font = UIFont.systemFont(ofSize: 34, weight: .heavy)
            for s in walls where s.len > 0.15 {
                let m = CGPoint(x: (s.a.x + s.b.x) / 2, y: (s.a.y + s.b.y) / 2)
                var dx = m.x - mid.x, dy = m.y - mid.y
                let n = max(sqrt(dx * dx + dy * dy), 0.0001); dx /= n; dy /= n
                let pm = P(m)
                let t = NSAttributedString(string: SiteTools.feetInches(s.len),
                                           attributes: [.font: font, .foregroundColor: UIColor(white: 0.1, alpha: 1)])
                let sz = t.size()
                let c = CGPoint(x: pm.x + dx * 46, y: pm.y + dy * 46)
                let box = CGRect(x: c.x - sz.width / 2 - 10, y: c.y - sz.height / 2 - 4, width: sz.width + 20, height: sz.height + 8)
                UIColor(white: 1, alpha: 0.92).setFill(); UIBezierPath(roundedRect: box, cornerRadius: 8).fill()
                t.draw(at: CGPoint(x: box.minX + 10, y: box.minY + 4))
            }

            // header
            let sqft = Double(area) * 10.7639104
            NSAttributedString(string: title, attributes: [.font: UIFont.systemFont(ofSize: 48, weight: .heavy),
                                                           .foregroundColor: UIColor.black]).draw(at: CGPoint(x: 60, y: 44))
            var facts: [String] = []
            if sqft > 0 { facts.append(String(format: "%.1f sq ft", sqft)) }
            if ceiling > 0 { facts.append("Ceiling " + SiteTools.feetInches(ceiling)) }
            facts.append("\(walls.count) walls · \(doors.count) doors · \(windows.count) windows")
            NSAttributedString(string: facts.joined(separator: "   ·   "),
                               attributes: [.font: UIFont.systemFont(ofSize: 32, weight: .bold),
                                            .foregroundColor: UIColor(white: 0.35, alpha: 1)]).draw(at: CGPoint(x: 60, y: 112))
            NSAttributedString(string: "Scanned with LiDAR. Good for layout and estimates; tape-check before cutting.",
                               attributes: [.font: UIFont.systemFont(ofSize: 26, weight: .semibold),
                                            .foregroundColor: UIColor(white: 0.5, alpha: 1)]).draw(at: CGPoint(x: 60, y: H - 64))
        }
    }
}
#endif

#endif
