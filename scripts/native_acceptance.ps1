<##
Native acceptance runner for synthetic Word, Excel, and Visio artifacts.

This Windows-only entrypoint owns the complete native boundary: it creates a fresh COM
application, builds synthetic content, saves and reopens an editable artifact, exports a PDF,
renders that PDF with Poppler, and writes one relative-path evidence record. It never kills a
process, changes a license, edits the registry, or touches a user-owned application instance.

Example:
  pwsh -NoProfile -File scripts/native_acceptance.ps1 -Artifact all -OutputRoot C:\Temp\academic-workstation-v020

The output root should be a private staging directory. Supply -VisualReviewRoot after inspecting
the rendered PNGs; it must contain word.json, excel.json, and/or visio.json page observations.
Supply -RecoveryEvidence after a project-level backup/restore rehearsal to close the L6 gate.
##>

[CmdletBinding()]
param(
    [ValidateSet("all", "word", "excel", "visio")]
    [string]$Artifact = "all",
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [string]$VisualReviewRoot = "",
    [string]$RecoveryEvidence = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- COM 与进程边界 ---
function Release-ComObject {
    param([AllowNull()][object]$Value)
    if ($null -ne $Value -and [System.Runtime.InteropServices.Marshal]::IsComObject($Value)) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($Value)
    }
}


function Get-ProcessIds {
    param([Parameter(Mandatory = $true)][string]$Name)
    $processIds = [System.Collections.Generic.List[int]]::new()
    foreach ($process in @(Get-Process -Name $Name -ErrorAction SilentlyContinue)) {
        if ($null -ne $process) { [void]$processIds.Add([int]$process.Id) }
    }
    return $processIds.ToArray()
}


function Set-NativeApplicationSafety {
    param([Parameter(Mandatory = $true)][object]$Application)
    $visibility = "hidden"
    try {
        $Application.Visible = $false
    } catch {
        # 某些 Office 构建拒绝隐藏窗口；保留最小化可见窗口并把兼容性事实写入证据。
        $Application.Visible = $true
        try { $Application.WindowState = 2 } catch { }
        $visibility = "visible-minimized-fallback"
    }
    try { $Application.DisplayAlerts = 0 } catch { }
    try { $Application.AutomationSecurity = 3 } catch { }
    return $visibility
}


function New-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][bool]$Required,
        [string]$Details = ""
    )
    $check = [ordered]@{ name = $Name; status = $Status; required = $Required }
    if ($Details) { $check.details = $Details }
    return $check
}


function Get-ArtifactRecord {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Root
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    $item = Get-Item -LiteralPath $Path
    if ($item.LinkType) { return $null }
    $relative = [IO.Path]::GetRelativePath($Root, $item.FullName).Replace("\", "/")
    return [ordered]@{
        path = $relative
        bytes = [int64]$item.Length
        sha256 = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}


function Get-VisualReview {
    param([Parameter(Mandatory = $true)][string]$ArtifactName)
    if ([string]::IsNullOrWhiteSpace($VisualReviewRoot)) { return $null }
    $reviewPath = Join-Path $VisualReviewRoot ("{0}.json" -f $ArtifactName)
    if (-not (Test-Path -LiteralPath $reviewPath -PathType Leaf)) { return $null }
    $parsed = Get-Content -LiteralPath $reviewPath -Raw | ConvertFrom-Json
    if ($parsed.PSObject.Properties.Name -contains "pages") { return @($parsed.pages) }
    return @($parsed)
}


# --- PDF 结构、渲染和人工复核接合 ---
function Invoke-PdfQa {
    param(
        [Parameter(Mandatory = $true)][string]$PdfPath,
        [Parameter(Mandatory = $true)][string]$ArtifactRoot,
        [Parameter(Mandatory = $true)][string]$ArtifactName
    )
    $checks = [System.Collections.Generic.List[object]]::new()
    $warnings = [System.Collections.Generic.List[string]]::new()
    $blockers = [System.Collections.Generic.List[string]]::new()
    $artifacts = [System.Collections.Generic.List[object]]::new()
    $rendered = [System.Collections.Generic.List[string]]::new()
    $pageCount = $null
    $pageGeometry = $null
    $review = Get-VisualReview $ArtifactName

    if (Test-Path -LiteralPath $PdfPath -PathType Leaf) {
        [void]$checks.Add((New-Check "PDF file exists" "PASS" $true "Native export created a regular PDF."))
        $record = Get-ArtifactRecord $PdfPath $ArtifactRoot
        if ($null -ne $record) { [void]$artifacts.Add($record) }
    } else {
        [void]$checks.Add((New-Check "PDF file exists" "FAIL" $true "Native export did not create the expected PDF."))
    }

    $pdfinfoCommand = Get-Command pdfinfo -ErrorAction SilentlyContinue
    if ($null -eq $pdfinfoCommand) {
        [void]$checks.Add((New-Check "pdfinfo available" "NOT_RUN" $false "Poppler pdfinfo is not on PATH."))
        [void]$blockers.Add("pdfinfo is required for PDF structure inspection")
    } elseif (Test-Path -LiteralPath $PdfPath -PathType Leaf) {
        $infoOutput = @(& $pdfinfoCommand.Source $PdfPath 2>&1)
        $pageLine = ($infoOutput | Where-Object { $_ -match "^Pages:\s*\d+" } | Select-Object -First 1)
        $sizeLine = ($infoOutput | Where-Object { $_ -match "^Page size:\s*[0-9.]+\s+x\s+[0-9.]+" } | Select-Object -First 1)
        $pageMatch = if ($pageLine) { [regex]::Match([string]$pageLine, "^Pages:\s*(?<count>\d+)") } else { $null }
        $sizeMatch = if ($sizeLine) { [regex]::Match([string]$sizeLine, "^Page size:\s*(?<width>[0-9.]+)\s+x\s+(?<height>[0-9.]+)") } else { $null }
        if ($LASTEXITCODE -eq 0 -and $null -ne $pageMatch -and $pageMatch.Success) {
            $pageCount = [int]$pageMatch.Groups["count"].Value
            [void]$checks.Add((New-Check "PDF structure parse" "PASS" $true "pdfinfo parsed the exported document."))
        } else {
            [void]$checks.Add((New-Check "PDF structure parse" "FAIL" $true "pdfinfo could not parse the exported document."))
        }
        if ($null -ne $sizeMatch -and $sizeMatch.Success) {
            $pageGeometry = "{0} x {1} points" -f $sizeMatch.Groups["width"].Value, $sizeMatch.Groups["height"].Value
            [void]$checks.Add((New-Check "page geometry" "PASS" $true $pageGeometry))
        } else {
            [void]$checks.Add((New-Check "page geometry" "FAIL" $true "pdfinfo did not report page dimensions."))
        }
    }

    $pdftoppmCommand = Get-Command pdftoppm -ErrorAction SilentlyContinue
    if ($null -eq $pdftoppmCommand) {
        [void]$checks.Add((New-Check "pdftoppm available" "NOT_RUN" $false "Poppler pdftoppm is not on PATH."))
        [void]$blockers.Add("pdftoppm is required for page rendering")
    } elseif ($null -ne $pageCount -and $pageCount -gt 0) {
        $renderRoot = Join-Path $ArtifactRoot "rendered-pdf"
        # A rerun may have fewer pages; remove only this runner's old page images before counting.
        if (Test-Path -LiteralPath $renderRoot -PathType Container) { Get-ChildItem -LiteralPath $renderRoot -Filter "page-*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force }
        $null = New-Item -ItemType Directory -Path $renderRoot -Force
        $prefix = Join-Path $renderRoot "page"
        & $pdftoppmCommand.Source -png -r 120 $PdfPath $prefix 2>&1 | Out-Null
        $renderedPages = @(Get-ChildItem -LiteralPath $renderRoot -Filter "page-*.png" -File | Sort-Object Name)
        foreach ($renderedPage in $renderedPages) {
            [void]$rendered.Add($renderedPage.FullName)
            $record = Get-ArtifactRecord $renderedPage.FullName $ArtifactRoot
            if ($null -ne $record) { [void]$artifacts.Add($record) }
        }
        $renderPass = $LASTEXITCODE -eq 0 -and $renderedPages.Count -eq $pageCount -and (@($renderedPages | Where-Object { $_.Length -le 0 }).Count -eq 0)
        [void]$checks.Add((New-Check "PDF page rendering" $(if ($renderPass) { "PASS" } else { "FAIL" }) $true ("Rendered {0} of {1} pages." -f $renderedPages.Count, $pageCount)))
    } else {
        [void]$checks.Add((New-Check "PDF page rendering" "NOT_RUN" $true "Rendering waits for a valid page count."))
    }

    if ($null -eq $review) {
        [void]$checks.Add((New-Check "page-by-page visual review" "NOT_RUN" $true ("Inspect rendered PNGs and supply {0}.json." -f $ArtifactName)))
    } elseif ($null -eq $pageCount -or $pageCount -lt 1) {
        [void]$checks.Add((New-Check "page-by-page visual review" "FAIL" $true "Visual review cannot be matched without a page count."))
    } else {
        $observedPages = @($review | ForEach-Object { [int]$_.page } | Sort-Object -Unique)
        $expectedPages = 1..$pageCount
        $pageSetMatches = (@(Compare-Object -ReferenceObject $expectedPages -DifferenceObject $observedPages).Count -eq 0 -and $observedPages.Count -eq $pageCount)
        $visualProblems = @($review | Where-Object { $_.blank -or $_.clipping -or $_.overlap -or $_.overflow })
        $visualPass = $pageSetMatches -and $visualProblems.Count -eq 0
        foreach ($item in $review) {
            if ($item.notes) {
                foreach ($note in @($item.notes)) { [void]$warnings.Add(("page {0}: {1}" -f $item.page, $note)) }
            }
        }
        [void]$checks.Add((New-Check "page-by-page visual review" $(if ($visualPass) { "PASS" } else { "FAIL" }) $true $(if ($visualPass) { "Every rendered page has an explicit review." } else { "Missing or flagged page review entry." })))
        if ($warnings.Count -gt 0) { [void]$warnings.Add("Visual review notes are non-blocking observations and remain visible.") }
    }

    return [ordered]@{
        checks = @($checks)
        warnings = @($warnings)
        blockers = @($blockers)
        artifacts = @($artifacts)
        rendered = @($rendered)
        visualReview = if ($null -eq $review) { @() } else { @($review) }
        pageCount = $pageCount
        pageGeometry = $pageGeometry
    }
}


# --- 统一证据闭环 ---
function Get-CheckStatus {
    param([object[]]$Checks, [Parameter(Mandatory = $true)][string]$Name)
    $match = @($Checks | Where-Object { $_.name -eq $Name } | Select-Object -Last 1)
    if ($match.Count -eq 0) { return "UNAVAILABLE" }
    return [string]$match[0].status
}


function Complete-Evidence {
    param(
        [Parameter(Mandatory = $true)][string]$ArtifactType,
        [Parameter(Mandatory = $true)][string]$ArtifactName,
        [Parameter(Mandatory = $true)][string]$ArtifactRoot,
        [Parameter(Mandatory = $true)][string]$NativeApplication,
        [Parameter(Mandatory = $true)][string]$NativeVersion,
        [Parameter(Mandatory = $true)][string]$VisibilityMode,
        [Parameter(Mandatory = $true)][object[]]$Checks,
        [AllowEmptyCollection()][object[]]$Artifacts = @(),
        [AllowEmptyCollection()][object[]]$VisualReview = @(),
        [AllowEmptyCollection()][object[]]$Warnings = @(),
        [AllowEmptyCollection()][object[]]$Blockers = @(),
        [AllowEmptyCollection()][object[]]$Fallbacks = @(),
        [string]$SourcePath,
        [string]$RoundtripPath,
        [string]$ExportPath,
        [int[]]$PreexistingPids = @(),
        [int[]]$PostPids = @(),
        [int[]]$PilotOwnedResidualPids = @(),
        [string]$ExecutionError = $null
    )
    $requiredFailures = @($Checks | Where-Object { $_.required -and $_.status -in @("FAIL", "BLOCKED", "NOT_RUN", "UNKNOWN") })
    $allWarnings = [System.Collections.Generic.List[string]]::new()
    foreach ($warning in $Warnings) { [void]$allWarnings.Add([string]$warning) }
    foreach ($fallback in $Fallbacks) { [void]$allWarnings.Add(("Fallback used at {0}: {1}" -f $fallback.step, $fallback.fallback)) }
    if ($PilotOwnedResidualPids.Count -gt 0) { [void]$allWarnings.Add("Pilot-owned process remained after bounded cleanup; no termination was attempted.") }
    $recoveryStatus = "NOT_RUN"
    $deferred = @("Backup/restore rehearsal is a separate release gate.")
    if (-not [string]::IsNullOrWhiteSpace($RecoveryEvidence) -and (Test-Path -LiteralPath $RecoveryEvidence -PathType Leaf)) {
        $recoveryRecord = Get-Content -LiteralPath $RecoveryEvidence -Raw | ConvertFrom-Json
        if ($recoveryRecord.PSObject.Properties.Name -contains "status") { $recoveryStatus = [string]$recoveryRecord.status }
        if ($recoveryRecord.PSObject.Properties.Name -contains "acceptance" -and $null -ne $recoveryRecord.acceptance.gates.recovery) { $recoveryStatus = [string]$recoveryRecord.acceptance.gates.recovery }
        if ($recoveryStatus -eq "PASS") { $deferred = @() }
    }
    $preexistingPidList = [System.Collections.Generic.List[int]]::new(); foreach ($processIdValue in @($PreexistingPids)) { if ($null -ne $processIdValue) { [void]$preexistingPidList.Add([int]$processIdValue) } }
    $postPidList = [System.Collections.Generic.List[int]]::new(); foreach ($processIdValue in @($PostPids)) { if ($null -ne $processIdValue) { [void]$postPidList.Add([int]$processIdValue) } }
    $residualPidList = [System.Collections.Generic.List[int]]::new(); foreach ($processIdValue in @($PilotOwnedResidualPids)) { if ($null -ne $processIdValue) { [void]$residualPidList.Add([int]$processIdValue) } }
    $visualReviewList = [System.Collections.Generic.List[object]]::new(); foreach ($review in @($VisualReview)) { if ($null -ne $review) { [void]$visualReviewList.Add($review) } }
    $fallbackList = [System.Collections.Generic.List[object]]::new(); foreach ($fallback in @($Fallbacks)) { if ($null -ne $fallback) { [void]$fallbackList.Add($fallback) } }
    $status = if ($Blockers.Count -gt 0) { "BLOCKED" } elseif ($requiredFailures.Count -gt 0) { "FAIL" } elseif ($allWarnings.Count -gt 0 -or $deferred.Count -gt 0) { "PASS_WITH_WARNING" } else { "PASS" }
    $nativeOpen = Get-CheckStatus $Checks "native open and structured inspection"
    $roundtrip = Get-CheckStatus $Checks "native round-trip"
    $export = Get-CheckStatus $Checks "native PDF export"
    $visual = Get-CheckStatus $Checks "page-by-page visual review"
    $structural = Get-CheckStatus $Checks "native structure"
    if ($structural -eq "UNAVAILABLE") { $structural = Get-CheckStatus $Checks "structural parse" }
    $highestLevel = if ($visual -eq "PASS" -and $recoveryStatus -eq "PASS" -and $Artifacts.Count -gt 0) { "L6" } elseif ($visual -eq "PASS") { "L5" } elseif ($export -eq "PASS") { "L4" } elseif ($roundtrip -eq "PASS") { "L3" } elseif ($nativeOpen -eq "PASS") { "L2" } else { "L1" }
    $evidence = [ordered]@{
        schemaVersion = "1.0"
        origin = "CURRENT_RUN"
        artifactType = $ArtifactType
        task = ("Synthetic {0} native acceptance" -f $ArtifactName)
        generatedAt = [DateTime]::UtcNow.ToString("o")
        platform = "Windows"
        nativeApplication = $NativeApplication
        nativeApplicationVersion = $NativeVersion
        sourcePath = $SourcePath
        roundtripPath = $RoundtripPath
        exportPath = $ExportPath
        route = [ordered]@{ targetFormat = $ArtifactType; nativeRequired = $true; structuredSourcePreserved = $true }
        acceptance = [ordered]@{
            highestLevel = $highestLevel
            gates = [ordered]@{
                generate = Get-CheckStatus $Checks "synthetic artifact build"
                parse = Get-CheckStatus $Checks "structural parse"
                nativeOpen = $nativeOpen
                roundtrip = $roundtrip
                export = $export
                structuralQA = $structural
                visualQA = $visual
                evidence = if ($Artifacts.Count -gt 0) { "PASS" } else { "FAIL" }
                recovery = $recoveryStatus
            }
        }
        checks = @($Checks)
        artifacts = @($Artifacts)
        visualReview = $visualReviewList
        warnings = @($allWarnings)
        deferred = @($deferred)
        blockers = @($Blockers)
        fallbacks = $fallbackList
        processBoundary = [ordered]@{
            preexistingPids = $preexistingPidList
            postPids = $postPidList
            pilotOwnedResidualPids = $residualPidList
            userProcessesUntouched = $true
            taskTerminationUsed = $false
        }
        visibilityMode = $VisibilityMode
        executionError = $ExecutionError
        status = $status
    }
    $evidencePath = Join-Path $ArtifactRoot "native-evidence.json"
    $evidence | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $evidencePath -Encoding utf8
    return $evidence
}


# --- Word DOCX 原生链 ---
function Invoke-WordAcceptance {
    $artifactRoot = Join-Path $OutputRoot "word"
    $null = New-Item -ItemType Directory -Path $artifactRoot -Force
    $inputPath = Join-Path $artifactRoot "academic-workstation-word-pilot.docx"
    $roundtripPath = Join-Path $artifactRoot "academic-workstation-word-roundtrip.docx"
    $pdfPath = Join-Path $artifactRoot "academic-workstation-word.pdf"
    $fallbackPdfPath = Join-Path $artifactRoot "academic-workstation-word-fallback.pdf"
    $picturePath = Join-Path $artifactRoot "synthetic-marker.png"
    $pngBytes = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    [IO.File]::WriteAllBytes($picturePath, $pngBytes)
    $beforePids = Get-ProcessIds "WINWORD"
    $afterPids = @()
    $residualPids = @()
    $checks = [System.Collections.Generic.List[object]]::new()
    $artifacts = [System.Collections.Generic.List[object]]::new()
    $warnings = [System.Collections.Generic.List[string]]::new()
    $fallbacks = [System.Collections.Generic.List[object]]::new()
    $blockers = [System.Collections.Generic.List[string]]::new()
    $word = $null; $document = $null; $reopened = $null; $inspection = $null; $selection = $null; $table = $null; $range = $null; $header = $null; $footer = $null
    $version = "unknown"; $visibility = "not-started"; $finalPdfPath = $null; $executionError = $null; $pdfQa = $null
    try {
        $word = New-Object -ComObject Word.Application
        $version = [string]$word.Version
        $visibility = Set-NativeApplicationSafety $word
        $document = $word.Documents.Add()
        $selection = $word.Selection
        # 中文 Office 可能将内置样式本地化；用字体属性表达标题，避免依赖本地化样式名。
        $selection.Font.Size = 20
        $selection.Font.Bold = $true
        $selection.TypeText("Academic Workstation Word synthetic pilot")
        $selection.TypeParagraph()
        $selection.Font.Size = 11
        $selection.Font.Bold = $false
        $selection.TypeText("SYNTHETIC TEST DATA | NOT RESEARCH RESULTS")
        $selection.TypeParagraph()
        $selection.TypeText("This document exercises headings, mixed text, lists, a table, an embedded picture, headers, footers, and page breaks.")
        $selection.TypeParagraph()
        $selection.TypeText("• Editable paragraph with Unicode marker and English text.")
        $selection.TypeParagraph()
        $selection.TypeText("1. Numbered acceptance step")
        $selection.TypeParagraph()
        $range = $document.Range($document.Content.End - 1, $document.Content.End - 1)
        $table = $document.Tables.Add($range, 4, 3)
        $table.Cell(1, 1).Range.Text = "Gate"; $table.Cell(1, 2).Range.Text = "Observed"; $table.Cell(1, 3).Range.Text = "State"
        $table.Cell(2, 1).Range.Text = "Paragraphs"; $table.Cell(2, 2).Range.Text = "mixed"; $table.Cell(2, 3).Range.Text = "PASS"
        $table.Cell(3, 1).Range.Text = "Picture"; $table.Cell(3, 2).Range.Text = "embedded"; $table.Cell(3, 3).Range.Text = "PASS"
        $table.Cell(4, 1).Range.Text = "Source"; $table.Cell(4, 2).Range.Text = "synthetic"; $table.Cell(4, 3).Range.Text = "SAFE"
        $range = $document.Range($document.Content.End - 1, $document.Content.End - 1)
        [void]$document.InlineShapes.AddPicture($picturePath, $false, $true, $range)
        $selection = $word.Selection
        $selection.SetRange($document.Content.End - 1, $document.Content.End - 1)
        $selection.InsertBreak(7)
        $selection.TypeText("Page 2 — structural acceptance markers")
        $selection.TypeParagraph()
        $selection.TypeText("Heading 1: Editable structure")
        $selection.TypeParagraph()
        $selection.TypeText("The paragraph, table, and picture remain native Word objects after the round-trip.")
        $selection.InsertBreak(7)
        $selection.TypeText("Page 3 — export and recovery markers")
        $selection.TypeParagraph()
        $selection.TypeText("The PDF is a derivative QA surface; the DOCX remains the editable source artifact.")
        $header = $document.Sections.Item(1).Headers.Item(1).Range
        $header.Text = "Academic Workstation | SYNTHETIC TEST DATA"
        $footer = $document.Sections.Item(1).Footers.Item(1).Range
        $footer.Text = "NOT RESEARCH RESULTS | Page "
        [void]$footer.Fields.Add($footer, 33)
        [void]$document.SaveAs2($inputPath, 16)
        [void]$checks.Add((New-Check "synthetic artifact build" "PASS" $true "DOCX was created by Microsoft Word."))
        [void]$checks.Add((New-Check "structural parse" $(if ($document.Paragraphs.Count -gt 5 -and $document.Tables.Count -eq 1 -and $document.InlineShapes.Count -eq 1) { "PASS" } else { "FAIL" }) $true ("paragraphs={0}; tables={1}; pictures={2}" -f $document.Paragraphs.Count, $document.Tables.Count, $document.InlineShapes.Count)))
        [void]$document.Close(0); Release-ComObject $document; $document = $null
        $reopened = $word.Documents.Open($inputPath, $false, $false, $false)
        [void]$reopened.SaveAs2($roundtripPath, 16)
        [void]$reopened.Close(0); Release-ComObject $reopened; $reopened = $null
        $inspection = $word.Documents.Open($roundtripPath, $false, $false, $false)
        $pageCount = [int]$inspection.ComputeStatistics(2)
        $roundtripPass = $pageCount -ge 3 -and $inspection.Tables.Count -eq 1 -and $inspection.InlineShapes.Count -eq 1 -and $inspection.Content.Text -match "SYNTHETIC TEST DATA"
        [void]$checks.Add((New-Check "native open and structured inspection" $(if ($roundtripPass) { "PASS" } else { "FAIL" }) $true ("pages={0}; tables={1}; pictures={2}" -f $pageCount, $inspection.Tables.Count, $inspection.InlineShapes.Count)))
        [void]$checks.Add((New-Check "native round-trip" $(if ($roundtripPass) { "PASS" } else { "FAIL" }) $true "Word saved, closed, reopened, and retained key content."))
        try {
            [void]$inspection.ExportAsFixedFormat($pdfPath, 17)
            $finalPdfPath = $pdfPath
        } catch {
            [void]$fallbacks.Add([ordered]@{ step = "pdf-export"; primary = "Word.ExportAsFixedFormat"; error = $_.Exception.Message; fallback = "Word.SaveAs2(PDF)"; fallbackResult = "NOT_RUN" })
            [void]$inspection.SaveAs2($fallbackPdfPath, 17)
            $finalPdfPath = $fallbackPdfPath
            $fallbacks[$fallbacks.Count - 1].fallbackResult = "PASS"
        }
        [void]$checks.Add((New-Check "native PDF export" $(if ($null -ne $finalPdfPath -and (Test-Path -LiteralPath $finalPdfPath -PathType Leaf)) { "PASS" } else { "FAIL" }) $true "PDF export completed in Word."))
        $pdfQa = Invoke-PdfQa $finalPdfPath $artifactRoot "word"
        foreach ($check in $pdfQa.checks) { [void]$checks.Add($check) }
        foreach ($record in $pdfQa.artifacts) { [void]$artifacts.Add($record) }
        foreach ($warning in $pdfQa.warnings) { [void]$warnings.Add($warning) }
        foreach ($blocker in $pdfQa.blockers) { [void]$blockers.Add($blocker) }
        $inspection.Close(0); Release-ComObject $inspection; $inspection = $null
        $nativeRecord = Get-ArtifactRecord $inputPath $artifactRoot; if ($null -ne $nativeRecord) { [void]$artifacts.Add($nativeRecord) }
        $nativeRecord = Get-ArtifactRecord $roundtripPath $artifactRoot; if ($null -ne $nativeRecord) { [void]$artifacts.Add($nativeRecord) }
    } catch {
        $executionError = $_.Exception.Message
        [void]$checks.Add((New-Check "native acceptance execution" "FAIL" $true $executionError))
    } finally {
        foreach ($value in @($header, $footer, $range, $table, $selection, $inspection, $reopened, $document)) { if ($null -ne $value) { try { if ($value.PSObject.Methods.Name -contains "Close") { [void]$value.Close(0) } } catch { }; Release-ComObject $value } }
        if ($null -ne $word) { try { [void]$word.Quit() } catch { }; Release-ComObject $word }
        # Office COM releases can finish asynchronously; wait within a bounded window before measuring residual PIDs.
        [GC]::Collect(); [GC]::WaitForPendingFinalizers(); Start-Sleep -Seconds 10
        $afterPids = Get-ProcessIds "WINWORD"
        $residualPids = @($afterPids | Where-Object { $beforePids -notcontains $_ })
    }
    $evidence = Complete-Evidence "docx" "word" $artifactRoot "Microsoft Word" $version $visibility @($checks) @($artifacts) $(if ($null -ne $pdfQa) { @($pdfQa.visualReview) } else { @() }) @($warnings) @($blockers) @($fallbacks) "academic-workstation-word-pilot.docx" "academic-workstation-word-roundtrip.docx" $(if ($finalPdfPath) { Split-Path -Leaf $finalPdfPath } else { "" }) $beforePids $afterPids $residualPids $executionError
    return $evidence
}


# --- Excel XLSX 原生链 ---
function Invoke-ExcelAcceptance {
    $artifactRoot = Join-Path $OutputRoot "excel"
    $null = New-Item -ItemType Directory -Path $artifactRoot -Force
    $inputPath = Join-Path $artifactRoot "academic-workstation-excel-pilot.xlsx"
    $roundtripPath = Join-Path $artifactRoot "academic-workstation-excel-roundtrip.xlsx"
    $pdfPath = Join-Path $artifactRoot "academic-workstation-excel.pdf"
    $fallbackPdfPath = Join-Path $artifactRoot "academic-workstation-excel-fallback.pdf"
    $beforePids = Get-ProcessIds "EXCEL"; $afterPids = @(); $residualPids = @()
    $checks = [System.Collections.Generic.List[object]]::new(); $artifacts = [System.Collections.Generic.List[object]]::new()
    $warnings = [System.Collections.Generic.List[string]]::new(); $fallbacks = [System.Collections.Generic.List[object]]::new(); $blockers = [System.Collections.Generic.List[string]]::new()
    $excel = $null; $book = $null; $reopened = $null; $data = $null; $analysis = $null; $dashboard = $null; $analysisAgain = $null; $dashboardAgain = $null; $chartObject = $null
    $version = "unknown"; $visibility = "not-started"; $finalPdfPath = $null; $executionError = $null; $pdfQa = $null
    try {
        $excel = New-Object -ComObject Excel.Application; $version = [string]$excel.Version; $visibility = Set-NativeApplicationSafety $excel
        $book = $excel.Workbooks.Add()
        $data = $book.Worksheets.Item(1); $data.Name = "Data"
        $analysis = $book.Worksheets.Add(); $analysis.Name = "Analysis"
        $dashboard = $book.Worksheets.Add(); $dashboard.Name = "Dashboard"
        $headers = @("Category", "Count", "Score", "Date", "Percent", "Blank")
        for ($column = 1; $column -le $headers.Count; $column++) { $data.Cells.Item(1, $column).Value2 = $headers[$column - 1] }
        $categories = @("Alpha", "Beta", "Gamma", "Delta", "Epsilon")
        for ($row = 2; $row -le 26; $row++) {
            $data.Cells.Item($row, 1).Value2 = $categories[($row - 2) % $categories.Count]
            # Excel's PowerShell COM binder rejects Int32 for Value2; cast numeric cells to Double so they remain numeric in Excel.
            $data.Cells.Item($row, 2).Value2 = [double]($row * 2)
            $data.Cells.Item($row, 3).Value2 = [double]([math]::Round(50 + (($row * 7) % 47) / 10, 1))
            $data.Cells.Item($row, 4).Value2 = [double]((Get-Date "2026-01-01").AddDays($row - 2).ToOADate())
            $data.Cells.Item($row, 5).Value2 = [double]((($row - 1) % 10) / 10)
            $data.Cells.Item($row, 6).Value2 = $null
        }
        $data.Range("D2:D26").NumberFormat = "yyyy-mm-dd"; $data.Range("E2:E26").NumberFormat = "0%"; $data.Columns.AutoFit() | Out-Null
        $analysisLabels = @("Metric", "SUM", "AVERAGE", "MIN", "MAX", "COUNT", "IF")
        for ($analysisRow = 1; $analysisRow -le $analysisLabels.Count; $analysisRow++) {
            $analysis.Cells.Item($analysisRow, 1).Value2 = $analysisLabels[$analysisRow - 1]
        }
        $analysis.Range("B2").Formula = "=SUM(Data!B2:B26)"
        $analysis.Range("B3").Formula = "=AVERAGE(Data!C2:C26)"
        $analysis.Range("B4").Formula = "=MIN(Data!C2:C26)"
        $analysis.Range("B5").Formula = "=MAX(Data!C2:C26)"
        $analysis.Range("B6").Formula = "=COUNT(Data!B2:B26)"
        $analysis.Range("B7").Formula = '=IF(B2>0,"PASS","FAIL")'
        $dashboard.Range("A1").Value2 = "Academic Workstation Excel synthetic dashboard"
        $dashboard.Range("A2").Value2 = "SYNTHETIC TEST DATA | NOT RESEARCH RESULTS"
        # Merge title rows and widen KPI columns so the exported dashboard keeps readable labels.
        [void]$dashboard.Range("A1:H1").Merge(); [void]$dashboard.Range("A2:H2").Merge()
        $dashboard.Columns.Item(1).ColumnWidth = 18; $dashboard.Columns.Item(2).ColumnWidth = 14
        $dashboardLabels = @("KPI", "Total count", "Average score", "Formula gate")
        for ($dashboardRow = 4; $dashboardRow -le 7; $dashboardRow++) {
            $dashboard.Cells.Item($dashboardRow, 1).Value2 = $dashboardLabels[$dashboardRow - 4]
        }
        $dashboard.Range("B5").Formula = "=Analysis!B2"; $dashboard.Range("B6").Formula = "=Analysis!B3"; $dashboard.Range("B7").Formula = "=Analysis!B7"
        # Separate label and numeric arrays avoid PowerShell collapsing mixed nested arrays into Int32 values.
        $chartLabels = @("Group", "A", "B", "C", "D")
        $chartValues = @("Value", [double]42, [double]68, [double]55, [double]86)
        for ($chartRow = 0; $chartRow -lt $chartLabels.Count; $chartRow++) {
            $dashboard.Cells.Item($chartRow + 10, 1).Value2 = $chartLabels[$chartRow]
            if ($chartRow -eq 0) { $dashboard.Cells.Item($chartRow + 10, 2).Value2 = $chartValues[$chartRow] } else { $dashboard.Cells.Item($chartRow + 10, 2).Value2 = [double]$chartValues[$chartRow] }
        }
        $chartCreated = $false
        try {
            # Keep the chart inside the Dashboard print area so every category survives PDF export.
            $chartObject = $dashboard.ChartObjects().Add(260, 30, 300, 220)
            $chartObject.Chart.ChartType = 51
            $chartObject.Chart.HasTitle = $true
            $chartObject.Chart.ChartTitle.Text = "Synthetic measures"
            [void]$chartObject.Chart.SetSourceData($dashboard.Range("A10:B14"), 2)
            $chartCreated = $true
            Release-ComObject $chartObject; $chartObject = $null
        } catch {
            [void]$fallbacks.Add([ordered]@{ step = "excel-chart"; primary = "Excel.ChartObjects.Add"; error = $_.Exception.Message; fallback = "native editable bar shapes"; fallbackResult = "NOT_RUN" })
            for ($barIndex = 0; $barIndex -lt 4; $barIndex++) {
                $bar = $dashboard.Shapes.AddShape(1, 80 + ($barIndex * 100), 260 - (40 + ($barIndex * 20)), 55, (40 + ($barIndex * 20)))
                $bar.TextFrame2.TextRange.Text = @("A", "B", "C", "D")[$barIndex]
                Release-ComObject $bar
            }
            $fallbacks[$fallbacks.Count - 1].fallbackResult = "PASS"
            [void]$warnings.Add("Excel chart COM creation failed; editable native shapes preserve the synthetic visualization, so chart PASS is not claimed.")
        }
        $dashboard.PageSetup.PrintArea = $dashboard.Range("A1:H28").Address()
        $dashboard.PageSetup.FitToPagesWide = 1; $dashboard.PageSetup.FitToPagesTall = 1; $dashboard.PageSetup.Zoom = $false
        [void]$book.Worksheets.Select(); [void]$excel.CalculateFullRebuild(); [void]$book.SaveAs($inputPath, 51)
        [void]$checks.Add((New-Check "synthetic artifact build" "PASS" $true "XLSX was created by Microsoft Excel."))
        [void]$checks.Add((New-Check "structural parse" $(if ($book.Worksheets.Count -eq 3) { "PASS" } else { "FAIL" }) $true ("worksheets={0}" -f $book.Worksheets.Count)))
        [void]$book.Close($false); Release-ComObject $book; $book = $null
        $reopened = $excel.Workbooks.Open($inputPath, 0, $false)
        # Save a second XLSX through Excel, then inspect that reopened copy as the round-trip artifact.
        [void]$reopened.SaveAs($roundtripPath, 51)
        [void]$reopened.Close($false); Release-ComObject $reopened; $reopened = $null
        $reopened = $excel.Workbooks.Open($roundtripPath, 0, $false)
        [void]$excel.CalculateFullRebuild()
        $analysisAgain = $reopened.Worksheets.Item("Analysis")
        $dashboardAgain = $reopened.Worksheets.Item("Dashboard")
        $formulaPass = ([string]$analysisAgain.Range("B2").Formula -match "SUM") -and ([string]$analysisAgain.Range("B3").Formula -match "AVERAGE") -and ([string]$analysisAgain.Range("B7").Formula -match "IF")
        $valuePass = $null -ne $analysisAgain.Range("B2").Value2 -and $analysisAgain.Range("B2").Value2 -gt 0
        $chartCount = [int]$dashboardAgain.ChartObjects().Count
        $roundtripPass = $reopened.Worksheets.Count -eq 3 -and $formulaPass -and $valuePass
        [void]$checks.Add((New-Check "native open and structured inspection" $(if ($roundtripPass) { "PASS" } else { "FAIL" }) $true ("worksheets={0}; formula cache={1}" -f $reopened.Worksheets.Count, $analysisAgain.Range("B2").Value2)))
        [void]$checks.Add((New-Check "native round-trip" $(if ($roundtripPass) { "PASS" } else { "FAIL" }) $true "Excel recalculated, saved, closed, reopened, and retained formulas."))
        [void]$checks.Add((New-Check "native structure" $(if ($chartCount -gt 0 -or $fallbacks.Count -gt 0) { "PASS" } else { "FAIL" }) $true ("chartObjects={0}; editableFallback={1}" -f $chartCount, ($fallbacks.Count -gt 0))))
        # Select only Dashboard before exporting; grouped worksheet selection otherwise exports all three sheets.
        [void]$reopened.Worksheets.Item("Dashboard").Select(); [void]$reopened.Worksheets.Item("Dashboard").Activate()
        try { [void]$reopened.Worksheets.Item("Dashboard").ExportAsFixedFormat(0, $pdfPath); $finalPdfPath = $pdfPath } catch {
            [void]$fallbacks.Add([ordered]@{ step = "pdf-export"; primary = "Excel.Worksheet.ExportAsFixedFormat"; error = $_.Exception.Message; fallback = "Excel.Workbook.ExportAsFixedFormat"; fallbackResult = "NOT_RUN" })
            [void]$reopened.ExportAsFixedFormat(0, $fallbackPdfPath); $finalPdfPath = $fallbackPdfPath; $fallbacks[$fallbacks.Count - 1].fallbackResult = "PASS"
        }
        [void]$checks.Add((New-Check "native PDF export" $(if ($finalPdfPath -and (Test-Path -LiteralPath $finalPdfPath -PathType Leaf)) { "PASS" } else { "FAIL" }) $true "Excel exported the Dashboard worksheet to PDF."))
        $pdfQa = Invoke-PdfQa $finalPdfPath $artifactRoot "excel"
        foreach ($check in $pdfQa.checks) { [void]$checks.Add($check) }; foreach ($record in $pdfQa.artifacts) { [void]$artifacts.Add($record) }
        foreach ($warning in $pdfQa.warnings) { [void]$warnings.Add($warning) }; foreach ($blocker in $pdfQa.blockers) { [void]$blockers.Add($blocker) }
        # Close the inspected workbook before hashing; Excel keeps the round-trip file locked while open.
        Release-ComObject $analysisAgain; $analysisAgain = $null
        Release-ComObject $dashboardAgain; $dashboardAgain = $null
        [void]$reopened.Close($false); Release-ComObject $reopened; $reopened = $null
        $nativeRecord = Get-ArtifactRecord $inputPath $artifactRoot; if ($null -ne $nativeRecord) { [void]$artifacts.Add($nativeRecord) }
        $nativeRecord = Get-ArtifactRecord $roundtripPath $artifactRoot; if ($null -ne $nativeRecord) { [void]$artifacts.Add($nativeRecord) }
    } catch { $executionError = $_.Exception.Message; [void]$checks.Add((New-Check "native acceptance execution" "FAIL" $true $executionError))
    } finally {
        foreach ($value in @($analysisAgain, $dashboardAgain, $chartObject, $dashboard, $analysis, $data, $reopened, $book)) { if ($null -ne $value) { try { [void]$value.Close($false) } catch { }; Release-ComObject $value } }
        if ($null -ne $excel) { try { [void]$excel.Quit() } catch { }; Release-ComObject $excel }
        # Excel may keep a background calculation object briefly after Quit; measure only after bounded cleanup.
        [GC]::Collect(); [GC]::WaitForPendingFinalizers(); Start-Sleep -Seconds 10
        $afterPids = Get-ProcessIds "EXCEL"; $residualPids = @($afterPids | Where-Object { $beforePids -notcontains $_ })
    }
    return Complete-Evidence "xlsx" "excel" $artifactRoot "Microsoft Excel" $version $visibility @($checks) @($artifacts) $(if ($null -ne $pdfQa) { @($pdfQa.visualReview) } else { @() }) @($warnings) @($blockers) @($fallbacks) "academic-workstation-excel-pilot.xlsx" "academic-workstation-excel-roundtrip.xlsx" $(if ($finalPdfPath) { Split-Path -Leaf $finalPdfPath } else { "" }) $beforePids $afterPids $residualPids $executionError
}


# --- Visio VSDX 原生链 ---
function Invoke-VisioAcceptance {
    $artifactRoot = Join-Path $OutputRoot "visio"; $null = New-Item -ItemType Directory -Path $artifactRoot -Force
    $inputPath = Join-Path $artifactRoot "academic-workstation-visio-pilot.vsdx"; $roundtripPath = Join-Path $artifactRoot "academic-workstation-visio-roundtrip.vsdx"
    $pdfPath = Join-Path $artifactRoot "academic-workstation-visio.pdf"; $fallbackPdfPath = Join-Path $artifactRoot "academic-workstation-visio-fallback.pdf"
    $previewPath = Join-Path $artifactRoot "visio-preview.png"
    $beforePids = Get-ProcessIds "VISIO"; $afterPids = @(); $residualPids = @()
    $checks = [System.Collections.Generic.List[object]]::new(); $artifacts = [System.Collections.Generic.List[object]]::new(); $warnings = [System.Collections.Generic.List[string]]::new(); $fallbacks = [System.Collections.Generic.List[object]]::new(); $blockers = [System.Collections.Generic.List[string]]::new()
    $visio = $null; $document = $null; $reopened = $null; $page = $null; $version = "unknown"; $visibility = "not-started"; $finalPdfPath = $null; $executionError = $null; $pdfQa = $null
    try {
        $visio = New-Object -ComObject Visio.Application; $version = [string]$visio.Version; $visibility = Set-NativeApplicationSafety $visio
        $document = $visio.Documents.Add(""); $page = $document.Pages.Item(1)
        $page.PageSheet.CellsU("PageWidth").FormulaU = "11 in"; $page.PageSheet.CellsU("PageHeight").FormulaU = "8.5 in"
        $nativeShapes = [System.Collections.Generic.List[object]]::new()
        $start = $page.DrawRectangle(1, 7, 3, 6); $start.Text = "Start"; $start.CellsU("FillForegnd").FormulaU = "RGB(221,235,247)"; [void]$nativeShapes.Add($start)
        $input = $page.DrawOval(4, 7, 6, 6); $input.Text = "Input"; $input.CellsU("FillForegnd").FormulaU = "RGB(226,239,218)"; [void]$nativeShapes.Add($input)
        $process = $page.DrawRectangle(7, 7, 9, 6); $process.Text = "Process"; $process.CellsU("FillForegnd").FormulaU = "RGB(255,242,204)"; [void]$nativeShapes.Add($process)
        $review = $page.DrawOval(7, 4.5, 9, 3.5); $review.Text = "Review"; $review.CellsU("FillForegnd").FormulaU = "RGB(244,204,204)"; [void]$nativeShapes.Add($review)
        $archive = $page.DrawRectangle(4, 4.5, 6, 3.5); $archive.Text = "Archive"; $archive.CellsU("FillForegnd").FormulaU = "RGB(217,210,233)"; [void]$nativeShapes.Add($archive)
        # This Visio COM build exposes DrawRectangle and DrawOval, but not DrawRoundedRectangle; a rectangle keeps the sixth shape editable without a fake API call.
        $end = $page.DrawRectangle(1, 4.5, 3, 3.5); $end.Text = "End"; $end.CellsU("FillForegnd").FormulaU = "RGB(208,224,227)"; [void]$nativeShapes.Add($end)
        $connectors = [System.Collections.Generic.List[object]]::new()
        foreach ($line in @(@(3, 6, 4, 6), @(6, 6, 7, 6), @(8, 6, 8, 4.5), @(7, 4, 6, 4), @(4, 4, 3, 4))) {
            $connector = $page.DrawLine($line[0], $line[1], $line[2], $line[3]); $connector.CellsU("EndArrow").FormulaU = "4"; [void]$connectors.Add($connector)
        }
        # Release individual COM shape references before SaveAs/Quit so Visio cannot wait on hidden references.
        foreach ($connector in $connectors) { Release-ComObject $connector }; foreach ($shape in $nativeShapes) { Release-ComObject $shape }
        $connectors = $null; $nativeShapes = $null
        [void]$document.SaveAs($inputPath)
        [void]$checks.Add((New-Check "synthetic artifact build" "PASS" $true "VSDX was created by Microsoft Visio."))
        [void]$checks.Add((New-Check "structural parse" $(if ($page.Shapes.Count -ge 11) { "PASS" } else { "FAIL" }) $true ("shapes={0}" -f $page.Shapes.Count)))
        [void]$document.Close(); Release-ComObject $page; Release-ComObject $document; $page = $null; $document = $null
        $reopened = $visio.Documents.Open($inputPath); [void]$reopened.SaveAs($roundtripPath); [void]$reopened.Close(); Release-ComObject $reopened; $reopened = $null
        $reopened = $visio.Documents.Open($roundtripPath); $page = $reopened.Pages.Item(1)
        $shapeCount = [int]$page.Shapes.Count; $connectorCount = 0; $textCount = 0
        for ($shapeIndex = 1; $shapeIndex -le $page.Shapes.Count; $shapeIndex++) {
            $shape = $page.Shapes.Item($shapeIndex)
            if ([int]$shape.OneD -ne 0) { $connectorCount++ }; if ([string]$shape.Text) { $textCount++ }; Release-ComObject $shape
        }
        $roundtripPass = $reopened.Pages.Count -eq 1 -and $shapeCount -ge 11 -and $connectorCount -ge 5 -and $textCount -ge 6
        [void]$checks.Add((New-Check "native open and structured inspection" $(if ($roundtripPass) { "PASS" } else { "FAIL" }) $true ("pages={0}; shapes={1}; connectors={2}; text={3}" -f $reopened.Pages.Count, $shapeCount, $connectorCount, $textCount)))
        [void]$checks.Add((New-Check "native round-trip" $(if ($roundtripPass) { "PASS" } else { "FAIL" }) $true "Visio saved, closed, reopened, and retained native shapes/connectors."))
        [void]$checks.Add((New-Check "native structure" $(if ($roundtripPass) { "PASS" } else { "FAIL" }) $true "Editable shapes, arrows, labels, and page dimensions were inspected."))
        try { [void]$reopened.ExportAsFixedFormat(1, $pdfPath, 1, 0); $finalPdfPath = $pdfPath } catch {
            [void]$fallbacks.Add([ordered]@{ step = "pdf-export"; primary = "Visio.ExportAsFixedFormat"; error = $_.Exception.Message; fallback = "Visio.SaveAs(PDF)"; fallbackResult = "NOT_RUN" })
            [void]$reopened.SaveAs($fallbackPdfPath); $finalPdfPath = $fallbackPdfPath; $fallbacks[$fallbacks.Count - 1].fallbackResult = "PASS"
        }
        [void]$checks.Add((New-Check "native PDF export" $(if ($finalPdfPath -and (Test-Path -LiteralPath $finalPdfPath -PathType Leaf)) { "PASS" } else { "FAIL" }) $true "Visio exported a PDF derivative."))
        try { [void]$page.Export($previewPath); $previewRecord = Get-ArtifactRecord $previewPath $artifactRoot; if ($null -ne $previewRecord) { [void]$artifacts.Add($previewRecord) } } catch { [void]$warnings.Add("Visio preview export was unavailable; PDF rendering remains the visual surface.") }
        $pdfQa = Invoke-PdfQa $finalPdfPath $artifactRoot "visio"
        foreach ($check in $pdfQa.checks) { [void]$checks.Add($check) }; foreach ($record in $pdfQa.artifacts) { [void]$artifacts.Add($record) }; foreach ($warning in $pdfQa.warnings) { [void]$warnings.Add($warning) }; foreach ($blocker in $pdfQa.blockers) { [void]$blockers.Add($blocker) }
        # Close the inspected document before hashing it; Visio keeps the round-trip file locked while open.
        Release-ComObject $page; $page = $null
        [void]$reopened.Close(); Release-ComObject $reopened; $reopened = $null
        $nativeRecord = Get-ArtifactRecord $inputPath $artifactRoot; if ($null -ne $nativeRecord) { [void]$artifacts.Add($nativeRecord) }; $nativeRecord = Get-ArtifactRecord $roundtripPath $artifactRoot; if ($null -ne $nativeRecord) { [void]$artifacts.Add($nativeRecord) }
    } catch { $executionError = $_.Exception.Message; [void]$checks.Add((New-Check "native acceptance execution" "FAIL" $true $executionError))
    } finally {
        foreach ($value in @($page, $reopened, $document)) { if ($null -ne $value) { try { [void]$value.Close() } catch { }; Release-ComObject $value } }
        if ($null -ne $visio) { try { [void]$visio.Quit() } catch { }; Release-ComObject $visio }
        # Visio can finish its automation teardown after Quit; use a bounded observation window and never terminate it.
        [GC]::Collect(); [GC]::WaitForPendingFinalizers(); Start-Sleep -Seconds 10
        $afterPids = Get-ProcessIds "VISIO"; $residualPids = @($afterPids | Where-Object { $beforePids -notcontains $_ })
    }
    return Complete-Evidence "vsdx" "visio" $artifactRoot "Microsoft Visio" $version $visibility @($checks) @($artifacts) $(if ($null -ne $pdfQa) { @($pdfQa.visualReview) } else { @() }) @($warnings) @($blockers) @($fallbacks) "academic-workstation-visio-pilot.vsdx" "academic-workstation-visio-roundtrip.vsdx" $(if ($finalPdfPath) { Split-Path -Leaf $finalPdfPath } else { "" }) $beforePids $afterPids $residualPids $executionError
}


# --- 入口调度与安全退出 ---
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)
$null = New-Item -ItemType Directory -Path $OutputRoot -Force
$results = [System.Collections.Generic.List[object]]::new()
if ($Artifact -in @("all", "word")) { [void]$results.Add((Invoke-WordAcceptance)) }
if ($Artifact -in @("all", "excel")) { [void]$results.Add((Invoke-ExcelAcceptance)) }
if ($Artifact -in @("all", "visio")) { [void]$results.Add((Invoke-VisioAcceptance)) }
$results | ConvertTo-Json -Depth 14
if (@($results | Where-Object { $_.status -in @("FAIL", "BLOCKED") }).Count -gt 0) { exit 1 }
exit 0
