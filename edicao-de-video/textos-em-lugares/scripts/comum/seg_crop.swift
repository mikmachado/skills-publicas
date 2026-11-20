// recorte da pessoa num pedaço da imagem (x y w h em px do quadro), salvo no tamanho do quadro inteiro
import Foundation; import Vision; import CoreImage
let a = CommandLine.arguments
let inDir = URL(fileURLWithPath: a[1]), outDir = URL(fileURLWithPath: a[2])
let cx = Double(a[3])!, cy = Double(a[4])!, cw = Double(a[5])!, ch = Double(a[6])!
let files = try FileManager.default.contentsOfDirectory(atPath: inDir.path).filter { $0.hasSuffix(".jpg") }.sorted()
let ctx = CIContext(); let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate; req.outputPixelFormat = kCVPixelFormatType_OneComponent8
for f in files {
    guard let src = CIImage(contentsOf: inDir.appendingPathComponent(f)) else { continue }
    let H = src.extent.height
    let r = CGRect(x: cx, y: H - cy - ch, width: cw, height: ch)   // CI: origem embaixo
    let crop = src.cropped(to: r).transformed(by: CGAffineTransform(translationX: -r.minX, y: -r.minY))
    try VNImageRequestHandler(ciImage: crop, options: [:]).perform([req])
    guard let pb = req.results?.first?.pixelBuffer else { continue }
    var m = CIImage(cvPixelBuffer: pb)
    m = m.transformed(by: CGAffineTransform(scaleX: cw / m.extent.width, y: ch / m.extent.height))
         .transformed(by: CGAffineTransform(translationX: r.minX, y: r.minY))
    let bg = CIImage(color: .black).cropped(to: src.extent)
    m = m.composited(over: bg).cropped(to: src.extent)
    try ctx.writePNGRepresentation(of: m, to: outDir.appendingPathComponent(f.replacingOccurrences(of: ".jpg", with: ".png")), format: .L8, colorSpace: CGColorSpace(name: CGColorSpace.linearGray)!)
}
print("ok", files.count)
