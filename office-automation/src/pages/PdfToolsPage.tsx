import { FileText } from 'lucide-react'
import { ComingSoon } from '../components/ComingSoon'

export function PdfToolsPage() {
  return (
    <ComingSoon
      icon={FileText}
      title="PDF Tools"
      intro="Everyday PDF tasks without extra software, on phone or computer."
      features={[
        'Merge several PDFs into one document',
        'Split a PDF or extract selected pages',
        'Rotate and reorder pages',
        'Add page numbers, headers and a watermark',
        'Generate letters and forms from templates',
      ]}
    />
  )
}
