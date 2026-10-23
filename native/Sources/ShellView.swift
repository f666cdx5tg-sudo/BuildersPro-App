import SwiftUI
import WebKit

/// The whole screen is the live web app. Pop-up windows (iCloud sign-in, reports, photo views)
/// slide up in a sheet with Done and Share/Print.
struct ShellView: View {
    @ObservedObject var model: ShellModel

    var body: some View {
        WebHost(webView: model.webView)
            .ignoresSafeArea()
            .background(Color.black)
            .overlay {
                if model.offline { OfflineCard { model.reload() } }
            }
            .sheet(isPresented: Binding(get: { model.popup != nil },
                                        set: { if !$0 { model.closePopup() } })) {
                if let pop = model.popup { PopupView(model: model, webView: pop) }
            }
    }
}

private struct OfflineCard: View {
    let retry: () -> Void
    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "wifi.slash").font(.system(size: 40)).foregroundStyle(.white.opacity(0.85))
            Text("No connection").font(.title3.bold()).foregroundStyle(.white)
            Text("BuildersPro needs the internet once to load. After that it opens offline too.")
                .font(.callout).foregroundStyle(.white.opacity(0.7)).multilineTextAlignment(.center)
            Button("Try again", action: retry)
                .buttonStyle(.borderedProminent).controlSize(.large)
        }
        .padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.black)
    }
}

private struct PopupView: View {
    @ObservedObject var model: ShellModel
    let webView: WKWebView

    var body: some View {
        #if os(iOS)
        NavigationStack {
            WebHost(webView: webView)
                .ignoresSafeArea(edges: .bottom)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Done") { model.closePopup() }
                    }
                    ToolbarItem(placement: .primaryAction) {
                        Button { model.printPage(webView) } label: { Image(systemName: "square.and.arrow.up") }
                            .accessibilityLabel("Share or print")
                    }
                }
        }
        #else
        VStack(spacing: 0) {
            HStack {
                Button("Done") { model.closePopup() }.keyboardShortcut(.cancelAction)
                Spacer()
                Button { model.printPage(webView) } label: { Label("Print / PDF", systemImage: "printer") }
            }
            .padding(10)
            Divider()
            WebHost(webView: webView)
        }
        .frame(minWidth: 900, minHeight: 700)
        #endif
    }
}

#if os(iOS)
struct WebHost: UIViewRepresentable {
    let webView: WKWebView
    func makeUIView(context: Context) -> WKWebView { webView }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
#else
struct WebHost: NSViewRepresentable {
    let webView: WKWebView
    func makeNSView(context: Context) -> WKWebView { webView }
    func updateNSView(_ nsView: WKWebView, context: Context) {}
}
#endif
