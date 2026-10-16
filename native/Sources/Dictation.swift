import SwiftUI
import Speech
import AVFoundation

/// Voice notes: tap the red mic, talk, tap again — the words are saved as a note on the active job.
@MainActor
final class Dictation: ObservableObject {
    @Published var listening = false
    @Published var text = ""
    @Published var message = ""

    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let engine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    func start() {
        message = ""
        SFSpeechRecognizer.requestAuthorization { status in
            Task { @MainActor in
                guard status == .authorized else { self.message = "Turn on Speech Recognition for BuildersPro in Settings."; return }
                self.askMic { ok in
                    guard ok else { self.message = "Turn on the Microphone for BuildersPro in Settings."; return }
                    self.begin()
                }
            }
        }
    }

    private func askMic(_ done: @escaping (Bool) -> Void) {
        #if os(iOS)
        AVAudioApplication.requestRecordPermission { ok in Task { @MainActor in done(ok) } }
        #else
        AVCaptureDevice.requestAccess(for: .audio) { ok in Task { @MainActor in done(ok) } }
        #endif
    }

    private func begin() {
        guard let recognizer, recognizer.isAvailable else { message = "Voice isn't available right now."; return }
        text = ""
        #if os(iOS)
        let s = AVAudioSession.sharedInstance()
        try? s.setCategory(.record, mode: .measurement, options: .duckOthers)
        try? s.setActive(true, options: .notifyOthersOnDeactivation)
        #endif
        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        request = req
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in req.append(buffer) }
        engine.prepare()
        do { try engine.start() } catch { message = "Couldn't start the microphone."; return }
        task = recognizer.recognitionTask(with: req) { result, _ in
            if let result { Task { @MainActor in self.text = result.bestTranscription.formattedString } }
        }
        listening = true
    }

    /// Stops listening and returns what was heard.
    func stop() -> String {
        engine.stop()
        engine.inputNode.removeTap(onBus: 0)
        request?.endAudio()
        listening = false
        let heard = text.trimmingCharacters(in: .whitespacesAndNewlines)
        task?.finish()
        task = nil
        request = nil
        return heard
    }
}
