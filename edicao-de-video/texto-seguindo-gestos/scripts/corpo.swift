import Foundation
import Vision
import CoreImage
// uso: corpo <pasta quadros> <saida.json> -> por quadro: pulsos/cotovelos/ombros (pixels, y para baixo, conf)
let args = CommandLine.arguments
let inDir = URL(fileURLWithPath: args[1])
let files = try FileManager.default.contentsOfDirectory(atPath: inDir.path).filter { $0.hasSuffix(".jpg") }.sorted()
let req = VNDetectHumanBodyPoseRequest()
let joints: [(String, VNHumanBodyPoseObservation.JointName)] = [("lw", .leftWrist), ("rw", .rightWrist), ("le", .leftElbow), ("re", .rightElbow), ("ls", .leftShoulder), ("rs", .rightShoulder), ("nose", .nose)]
var out: [[String: [Double]]] = []
for f in files {
    let src = CIImage(contentsOf: inDir.appendingPathComponent(f))!
    let w = src.extent.width, h = src.extent.height
    try VNImageRequestHandler(ciImage: src, options: [:]).perform([req])
    var d: [String: [Double]] = [:]
    if let o = req.results?.first {
        for (n, j) in joints {
            if let p = try? o.recognizedPoint(j), p.confidence > 0.1 {
                d[n] = [Double(p.location.x * w), Double((1 - p.location.y) * h), Double(p.confidence)]
            }
        }
    }
    out.append(d)
}
try JSONSerialization.data(withJSONObject: out).write(to: URL(fileURLWithPath: args[2]))
print("ok", files.count)
