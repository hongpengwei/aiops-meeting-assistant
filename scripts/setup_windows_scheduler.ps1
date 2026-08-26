# =========================================================
# Windows 工作排程器一鍵註冊腳本 (PowerShell)
# =========================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = (Get-Item $ScriptDir).Parent.FullName

$DailyBat = Join-Path $ProjectDir "run_daily.bat"
$WeeklyBat = Join-Path $ProjectDir "run_weekly.bat"
$MonthlyBat = Join-Path $ProjectDir "run_monthly.bat"

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "⚙️ 正在註冊 Windows 工作排程器 (Task Scheduler)..." -ForegroundColor Cyan
Write-Host "專案目錄: $ProjectDir" -ForegroundColor Gray
Write-Host "=========================================================" -ForegroundColor Cyan

# 1. 註冊每日晨會排程 (週一到週五 08:30)
$DailyTaskName = "AIOps_Morning_Meeting_Daily"
$DailyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 08:30am
$DailyAction = New-ScheduledTaskAction -Execute $DailyBat -WorkingDirectory $ProjectDir
Register-ScheduledTask -TaskName $DailyTaskName -Trigger $DailyTrigger -Action $DailyAction -Description "每日晨會 Case 異常檢測與 AI 歸因簡報" -Force | Out-Null
Write-Host "✅ 每日晨會排程註冊成功！[名稱: $DailyTaskName | 時間: 週一~週五 08:30]" -ForegroundColor Green

# 2. 註冊每週課會排程 (每週一 09:00)
$WeeklyTaskName = "AIOps_Section_Meeting_Weekly"
$WeeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 09:00am
$WeeklyAction = New-ScheduledTaskAction -Execute $WeeklyBat -WorkingDirectory $ProjectDir
Register-ScheduledTask -TaskName $WeeklyTaskName -Trigger $WeeklyTrigger -Action $WeeklyAction -Description "每週課會 Case 趨勢比對與 AI 簡報" -Force | Out-Null
Write-Host "✅ 每週課會排程註冊成功！[名稱: $WeeklyTaskName | 時間: 每週一 09:00]" -ForegroundColor Green

# 3. 註冊每月課會排程 (每月 1 號 09:30)
$MonthlyTaskName = "AIOps_Section_Meeting_Monthly"
schtasks /Create /TN $MonthlyTaskName /TR "$MonthlyBat" /SC MONTHLY /D 1 /ST 09:30 /F | Out-Null
Write-Host "✅ 每月課會排程註冊成功！[名稱: $MonthlyTaskName | 時間: 每月 1 號 09:30]" -ForegroundColor Green

Write-Host "`n🎉 所有排程已就緒！系統將在會議開始前自動執行並推播。" -ForegroundColor Yellow
