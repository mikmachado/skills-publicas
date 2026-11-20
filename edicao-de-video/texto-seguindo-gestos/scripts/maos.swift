import Foundation
import Vision
import CoreImage
// uso: maos <pasta quadros> <saida.json>  -> por quadro: lista de mãos com pontas dos dedos (pixels, y para baixo)
let args = CommandLine.arguments
let inDir = URL(fileURLWithPath: args[1])
let files = try FileManager.default.contentsOfDirectory(atPath: inDir.path).filter { $0.hasSuffix(".jpg") }.sorted()
let req = VNDetectHumanHandPoseRequest()
req.maximumHandCount = 2
var out: [[[String: [Double]]]] = []
let joints: [(String, VNHumanHandPoseObservation.JointName)] = [("wrist", .wrist), ("indexTip", .indexTip), ("indexDIP", .indexDIP), ("indexPIP", .indexPIP), ("indexMCP", .indexMCP), ("middleTip", .middleTip), ("thumbTip", .thumbTip), ("middleMCP", .middleMCP)]
for f in files {
    let src = CIImage(contentsOf: inDir.appendingPathComponent(f))!
    let w = src.extent.width, h = src.extent.height
    try VNImageRequestHandler(ciImage: src, options: [:]).perform([req])
    var hands: [[String: [Double]]] = []
    for o in req.results ?? [] {
        var d: [String: [Double]] = [:]
        for (n, j) in joints {
            if let p = try? o.recognizedPoint(j), p.confidence > 0.1 {
                d[n] = [Double(p.location.x * w), Double((1 - p.location.y) * h), Double(p.confidence)]
            }
        }
        hands.append(d)
    }
    out.append(hands)
}
let data = try JSONSerialization.data(withJSONObject: out)
try data.write(to: URL(fileURLWithPath: args[2]))
print("ok", files.count)
