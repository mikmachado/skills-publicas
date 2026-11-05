// Recorte de "objeto em destaque" (o mesmo do "copiar objeto" das Fotos): pega a pessoa
// junto com o que ela toca ou em que está apoiada (cadeira, mesa, violão).
// Uso: swift seg_objetos.swift quadros/ mask_obj/
import Foundation
import Vision
import CoreImage
import ImageIO

let args = CommandLine.arguments
let inDir = URL(fileURLWithPath: args[1]), outDir = URL(fileURLWithPath: args[2])
let files = try FileManager.default.contentsOfDirectory(atPath: inDir.path).filter { $0.hasSuffix(".jpg") }.sorted()
let ctx = CIContext()
for f in files {
    let url = inDir.appendingPathComponent(f)
    guard let src = CIImage(contentsOf: url) else { continue }
    let h = VNImageRequestHandler(ciImage: src, options: [:])
    let req = VNGenerateForegroundInstanceMaskRequest()
    try h.perform([req])
    let out = outDir.appendingPathComponent(f.replacingOccurrences(of: ".jpg", with: ".png"))
    guard let obs = req.results?.first else {
        let vazio = CIImage(color: .black).cropped(to: src.extent)
        try ctx.writePNGRepresentation(of: vazio, to: out, format: .L8, colorSpace: CGColorSpace(name: CGColorSpace.linearGray)!)
        continue
    }
    let pb = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: h)
    var m = CIImage(cvPixelBuffer: pb)
    m = m.transformed(by: CGAffineTransform(scaleX: src.extent.width / m.extent.width, y: src.extent.height / m.extent.height))
    try ctx.writePNGRepresentation(of: m, to: out, format: .L8, colorSpace: CGColorSpace(name: CGColorSpace.linearGray)!)
}
print("done", files.count)
