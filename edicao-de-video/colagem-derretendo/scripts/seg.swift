import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
let inDir = URL(fileURLWithPath: args[1]), outDir = URL(fileURLWithPath: args[2])
let files = try FileManager.default.contentsOfDirectory(atPath: inDir.path).filter { $0.hasSuffix(".jpg") }.sorted()
let ctx = CIContext()
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
for f in files {
    let url = inDir.appendingPathComponent(f)
    guard let src = CIImage(contentsOf: url) else { continue }
    let h = VNImageRequestHandler(ciImage: src, options: [:])
    try h.perform([req])
    guard let pb = req.results?.first?.pixelBuffer else { continue }
    var m = CIImage(cvPixelBuffer: pb)
    m = m.transformed(by: CGAffineTransform(scaleX: src.extent.width / m.extent.width, y: src.extent.height / m.extent.height))
    let out = outDir.appendingPathComponent(f.replacingOccurrences(of: ".jpg", with: ".png"))
    try ctx.writePNGRepresentation(of: m, to: out, format: .L8, colorSpace: CGColorSpace(name: CGColorSpace.linearGray)!)
}
print("done", files.count)
