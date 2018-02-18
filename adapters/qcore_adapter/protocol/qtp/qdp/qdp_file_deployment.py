from construct import Struct, Int32ul, Pass, this, GreedyRange, Byte

FileDeploymentInquiryRequestMessage = Struct(
    'FileDeploymentInquiryRequestMessage' / Pass,
    'TODO' / GreedyRange(Byte)
)
