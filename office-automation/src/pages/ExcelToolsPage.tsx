import { FileSpreadsheet } from 'lucide-react'
import { ComingSoon } from '../components/ComingSoon'

export function ExcelToolsPage() {
  return (
    <ComingSoon
      icon={FileSpreadsheet}
      title="Excel Tools"
      intro="Work with Excel spreadsheets directly in your browser — files stay on your device unless you choose to save them."
      features={[
        'Open an .xlsx file and preview its sheets',
        'Create spreadsheets from ready-made office templates',
        'Merge several Excel files into one',
        'Clean data: remove duplicates and empty rows',
        'Export a sheet to PDF',
      ]}
    />
  )
}
