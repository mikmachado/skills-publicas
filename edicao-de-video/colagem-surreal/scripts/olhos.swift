// olhos: landmarks (Vision) -> olhos.json: [[face x,y,w,h, olhoE x,y, olhoD x,y, nariz x,y] ou null]
import Foundation
import Vision
import CoreImage
let a = CommandLine.arguments
let dir = URL(fileURLWithPath: a[1])
let passo = a.count > 3 ? Int(a[3]) ?? 1 : 1
let files = try FileManager.default.contentsOfDirectory(atPath: dir.path).filter { $0.hasSuffix(".jpg") }.sorted()
var out: [Any] = []
func c(_ r: VNFaceLandmarkRegion2D?, _ b: CGRect, _ W: CGFloat, _ H: CGFloat) -> [Double] {
  guard let r = r else { return [-1, -1] }
  let p = r.pointsInImage(imageSize: CGSize(width: W, height: H))
  let x = p.map { $0.x }.reduce(0, +) / CGFloat(p.count), y = p.map { $0.y }.reduce(0, +) / CGFloat(p.count)
  return [Double(x), Double(H - y)]
}
for (i, f) in files.enumerated() {
  if i % passo != 0 { out.append(NSNull()); continue }
  guard let img = CIImage(contentsOf: dir.appendingPathComponent(f)) else { out.append(NSNull()); continue }
  let W = img.extent.width, H = img.extent.height
  let req = VNDetectFaceLandmarksRequest()
  try VNImageRequestHandler(ciImage: img, options: [:]).perform([req])
  guard let face = (req.results ?? []).max(by: { $0.boundingBox.width < $1.boundingBox.width }), let lm = face.landmarks else { out.append(NSNull()); continue }
  let b = face.boundingBox
  var v: [Double] = [Double(b.minX * W), Double((1 - b.maxY) * H), Double(b.width * W), Double(b.height * H)]
  v += c(lm.leftEye, b, W, H); v += c(lm.rightEye, b, W, H); v += c(lm.nose, b, W, H)
  out.append(v)
}
try JSONSerialization.data(withJSONObject: out).write(to: URL(fileURLWithPath: a[2]))
print("faces:", out.filter { !($0 is NSNull) }.count, "/", files.count)
