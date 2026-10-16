import SwiftUI
import CoreLocation

/// Where you are + the weather there, for the Home header (same idea as the web app's header).
@MainActor
final class HeaderInfo: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var place = "Detecting location…"
    @Published var weather = "Loading weather…"
    @Published var icon = "🌡️"

    private let manager = CLLocationManager()
    private var lastFetch: Date?

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }

    func start() {
        if let t = lastFetch, Date().timeIntervalSince(t) < 600 { return }   // refresh at most every 10 minutes
        switch manager.authorizationStatus {
        case .notDetermined: manager.requestWhenInUseAuthorization()
        case .denied, .restricted: place = "Location is off — turn it on in Settings"; weather = "Weather needs your location"
        default: manager.requestLocation()
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        Task { @MainActor in self.start() }
    }

    nonisolated func locationManager(_ m: CLLocationManager, didUpdateLocations locs: [CLLocation]) {
        guard let loc = locs.last else { return }
        Task { @MainActor in
            self.lastFetch = Date()
            await self.lookUp(loc)
        }
    }

    nonisolated func locationManager(_ m: CLLocationManager, didFailWithError error: Error) {
        Task { @MainActor in self.place = "Couldn't find your location" }
    }

    private func lookUp(_ loc: CLLocation) async {
        // Address
        if let p = try? await CLGeocoder().reverseGeocodeLocation(loc).first {
            let street = [p.subThoroughfare, p.thoroughfare].compactMap { $0 }.joined(separator: " ")
            let city = [p.locality, p.administrativeArea].compactMap { $0 }.joined(separator: ", ")
            place = [street, city].filter { !$0.isEmpty }.joined(separator: ", ")
        } else {
            place = String(format: "%.4f, %.4f", loc.coordinate.latitude, loc.coordinate.longitude)
        }
        // Weather (Open-Meteo, free, no key)
        let url = URL(string: "https://api.open-meteo.com/v1/forecast?latitude=\(loc.coordinate.latitude)&longitude=\(loc.coordinate.longitude)&current=temperature_2m,weather_code,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph")!
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            if let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let cur = root["current"] as? [String: Any],
               let t = cur["temperature_2m"] as? Double {
                let code = (cur["weather_code"] as? Int) ?? -1
                let wind = (cur["wind_speed_10m"] as? Double) ?? 0
                let (emoji, text) = Self.describe(code)
                icon = emoji
                weather = "\(Int(t.rounded()))°F · \(text) · wind \(Int(wind.rounded())) mph"
            }
        } catch { weather = "Weather unavailable" }
    }

    private static func describe(_ c: Int) -> (String, String) {
        switch c {
        case 0: return ("☀️", "Clear")
        case 1, 2: return ("🌤️", "Mostly clear")
        case 3: return ("☁️", "Cloudy")
        case 45, 48: return ("🌫️", "Fog")
        case 51...57: return ("🌦️", "Drizzle")
        case 61...67: return ("🌧️", "Rain")
        case 71...77: return ("🌨️", "Snow")
        case 80...82: return ("🌦️", "Showers")
        case 85, 86: return ("🌨️", "Snow showers")
        case 95...99: return ("⛈️", "Thunderstorms")
        default: return ("🌡️", "Weather")
        }
    }
}
