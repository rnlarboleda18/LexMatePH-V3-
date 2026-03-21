$word = New-Object -ComObject Word.Application
$word.Visible = $false

$docs = @(
    "c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC Amendment\Amendment Direct_Implied to Criminal Procedure.docx",
    "c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC Amendment\Amendment o Special Proceeding.docx"
)

$out = "c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\scripts\docx_out.txt"
"Starting DOCX conversion..." | Out-File $out -Encoding utf8

foreach ($d in $docs) {
    if (Test-Path $d) {
        "Processing $d" | Out-File $out -Append -Encoding utf8
        try {
            $doc = $word.Documents.Open($d)
            $doc.Content.Text | Out-File $out -Append -Encoding utf8
            $doc.Close()
            "Done $d `n`n" | Out-File $out -Append -Encoding utf8
        } catch {
            "Error opening $d : $_" | Out-File $out -Append -Encoding utf8
        }
    } else {
        "File not found: $d" | Out-File $out -Append -Encoding utf8
    }
}

$word.Quit()
"Conversion complete." | Out-File $out -Append -Encoding utf8
