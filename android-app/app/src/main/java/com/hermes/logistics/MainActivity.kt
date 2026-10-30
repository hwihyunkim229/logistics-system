package com.logisticssystem.app

import android.Manifest
import android.app.Activity
import android.media.AudioManager
import android.media.ToneGenerator
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.AddBox
import androidx.compose.material.icons.filled.IndeterminateCheckBox
import androidx.compose.material.icons.filled.LocalOffer
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.camera.core.CameraSelector
import androidx.camera.view.LifecycleCameraController
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.UUID

private val HermesGreen = Color(0xFF006C5B)
private val HermesMint = Color(0xFF35D0A1)
private val HermesNavy = Color(0xFF102A2E)
private val HermesBackground = Color(0xFFF4F8F7)
private val HermesSurface = Color(0xFFFFFFFF)
private val HermesOutline = Color(0xFFD6E2DF)
private val HermesTextMuted = Color(0xFF61716F)
private val HermesOrange = Color(0xFFB34B2D)
private val HermesPurple = Color(0xFF4C5DB6)
private val HermesColorScheme = lightColorScheme(
    primary = HermesGreen,
    onPrimary = Color.White,
    secondary = HermesMint,
    onSecondary = HermesNavy,
    background = HermesBackground,
    onBackground = HermesNavy,
    surface = HermesSurface,
    onSurface = HermesNavy,
    outline = HermesOutline,
    error = Color(0xFFBA1A1A),
)

private enum class SessionState { CHECKING, LOGGED_OUT, LOGGED_IN }
private enum class InventoryAction { IN, OUT, LOT_REGISTER, SET_OUT }
private enum class MainTab { HOME, WORK, HISTORY, PROFILE }
private enum class SetComponent(val apiValue: String, val label: String) {
    PBA("PBA", "PBA"),
    OUTER("OUTER", "OUTER"),
    INNER("INNER", "INNER"),
    TOP_COVER("TOP_COVER", "TOP COVER"),
}

private data class QrMaterialData(
    val itemName: String = "",
    val itemCode: String = "",
    val receivedDate: String = "",
    val lot: String = "",
    val inspector: String = "",
)

private data class CompletionData(
    val action: InventoryAction,
    val item: InventoryItem,
    val quantity: Int,
    val result: MovementResult,
    val qrData: QrMaterialData?,
)

private data class SetAllocation(
    val component: SetComponent,
    val item: InventoryItem,
    val qrData: QrMaterialData,
    val qty: Int,
)

private fun detectSetComponent(vararg names: String): SetComponent? {
    val normalized = names.joinToString(" ")
        .uppercase()
        .replace('_', ' ')
        .replace('-', ' ')
    return when {
        "TOP COVER" in normalized || ("TOP" in normalized && "COVER" in normalized) -> SetComponent.TOP_COVER
        "OUTER" in normalized -> SetComponent.OUTER
        "INNER" in normalized -> SetComponent.INNER
        "PBA" in normalized -> SetComponent.PBA
        else -> null
    }
}

private fun setComponentColor(component: SetComponent): Color = when (component) {
    SetComponent.PBA -> Color(0xFF006C5B)
    SetComponent.OUTER -> Color(0xFF3157A4)
    SetComponent.INNER -> Color(0xFF7A4AA5)
    SetComponent.TOP_COVER -> Color(0xFFB35424)
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ApiClient.initialize(applicationContext)
        setContent {
            MaterialTheme(colorScheme = HermesColorScheme) {
                Surface(color = HermesBackground, modifier = Modifier.fillMaxSize()) {
                    Box(Modifier.fillMaxSize().safeDrawingPadding()) {
                        LogisticsApp()
                    }
                }
            }
        }
    }
}

@Composable
private fun LogisticsApp() {
    var sessionState by rememberSaveable {
        mutableStateOf(
            if (ApiClient.hasStoredSession()) SessionState.LOGGED_IN else SessionState.LOGGED_OUT
        )
    }

    when (sessionState) {
        SessionState.CHECKING -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        SessionState.LOGGED_OUT -> LoginScreen(onLogin = { sessionState = SessionState.LOGGED_IN })
        SessionState.LOGGED_IN -> InventoryScreen(
            onSessionExpired = { sessionState = SessionState.LOGGED_OUT },
            onLogout = {
                ApiClient.logout()
                sessionState = SessionState.LOGGED_OUT
            },
        )
    }
}

@Composable
private fun LoginScreen(onLogin: () -> Unit) {
    var username by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var passwordVisible by rememberSaveable { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var devServerUrl by rememberSaveable { mutableStateOf(ApiClient.baseUrl()) }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Logistics System", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
        Text(if (BuildConfig.IS_DEV) "DEV · 로컬 테스트 환경" else "현장 입고·출고", color = HermesGreen, fontWeight = FontWeight.Bold)
        if (BuildConfig.IS_DEV) {
            Spacer(Modifier.height(10.dp))
            OutlinedTextField(
                value = devServerUrl,
                onValueChange = { devServerUrl = it },
                label = { Text("DEV 서버 주소") },
                supportingText = { Text("노트북 Wi-Fi IP가 바뀌면 로그인 전에 수정하세요.") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        Spacer(Modifier.height(28.dp))
        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = { Text("아이디") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("비밀번호") },
            singleLine = true,
            visualTransformation = if (passwordVisible) {
                VisualTransformation.None
            } else {
                PasswordVisualTransformation()
            },
            trailingIcon = {
                IconButton(onClick = { passwordVisible = !passwordVisible }) {
                    Icon(
                        imageVector = if (passwordVisible) Icons.Filled.VisibilityOff else Icons.Filled.Visibility,
                        contentDescription = if (passwordVisible) "비밀번호 숨기기" else "비밀번호 보기",
                    )
                }
            },
            modifier = Modifier.fillMaxWidth(),
        )
        if (message.isNotBlank()) Text(message, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp))
        Spacer(Modifier.height(20.dp))
        Button(
            enabled = !loading && username.isNotBlank() && password.isNotBlank(),
            onClick = {
                if (BuildConfig.IS_DEV) {
                    val serverError = ApiClient.updateDevServerUrl(devServerUrl)
                    if (serverError != null) {
                        message = serverError
                        return@Button
                    }
                }
                loading = true
                message = ""
                scope.launch {
                    val result = withContext(Dispatchers.IO) { ApiClient.login(username.trim(), password) }
                    loading = false
                    when {
                        result.error != null -> message = result.error
                        result.requiresPasswordChange -> message = "웹사이트에서 비밀번호를 먼저 변경해 주세요."
                        else -> onLogin()
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (loading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(22.dp),
                    strokeWidth = 2.5.dp,
                    color = Color.White,
                )
            } else Text("로그인")
        }
    }
}

@Composable
private fun ActionButton(
    label: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    if (selected) {
        Button(onClick = onClick, modifier = modifier) { Text(label) }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier) { Text(label) }
    }
}

@Composable
private fun InventoryScreen(onSessionExpired: () -> Unit, onLogout: () -> Unit) {
    var keyword by rememberSaveable { mutableStateOf("") }
    var warehouse by rememberSaveable { mutableStateOf("창고재고") }
    var scanQty by rememberSaveable { mutableStateOf("1") }
    var action by rememberSaveable { mutableStateOf<InventoryAction?>(null) }
    var mainTab by rememberSaveable { mutableStateOf(MainTab.HOME) }
    var results by remember { mutableStateOf(emptyList<InventoryItem>()) }
    var selected by remember { mutableStateOf<InventoryItem?>(null) }
    var loading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var showScanner by remember { mutableStateOf(false) }
    var qrData by remember { mutableStateOf<QrMaterialData?>(null) }
    var showLotDetail by remember { mutableStateOf(false) }
    var completion by remember { mutableStateOf<CompletionData?>(null) }
    var history by remember { mutableStateOf(emptyList<InventoryHistoryItem>()) }
    var historyLoading by remember { mutableStateOf(false) }
    var historyMessage by remember { mutableStateOf("") }
    var showExitDialog by rememberSaveable { mutableStateOf(false) }
    var currentUser by remember { mutableStateOf(ApiClient.currentUser()) }
    var setTargetText by rememberSaveable { mutableStateOf("50") }
    var setActiveComponent by rememberSaveable { mutableStateOf(SetComponent.PBA) }
    var setActiveGrade by rememberSaveable { mutableStateOf("") }
    var setAllocations by remember { mutableStateOf(emptyList<SetAllocation>()) }
    var setReview by rememberSaveable { mutableStateOf(false) }
    var setSubmitting by remember { mutableStateOf(false) }
    var setMessage by remember { mutableStateOf("") }
    var setCompletion by remember { mutableStateOf<SetOutboundResult?>(null) }
    var lastSetAllocation by remember { mutableStateOf<SetAllocation?>(null) }
    var setRemarkOption by rememberSaveable { mutableStateOf("") }
    var setCustomRemark by rememberSaveable { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    var cameraGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        cameraGranted = granted
        if (granted) showScanner = true else message = "카메라 권한이 필요합니다."
    }

    LaunchedEffect(Unit) {
        val session = withContext(Dispatchers.IO) { ApiClient.checkSession() }
        if (session.error != null) {
            onSessionExpired()
        } else {
            currentUser = session.value.orEmpty().ifBlank { ApiClient.currentUser() }
        }
    }

    fun openScanner() {
        if (cameraGranted) showScanner = true
        else permissionLauncher.launch(Manifest.permission.CAMERA)
    }

    fun resetWork(nextAction: InventoryAction? = action, completionMessage: String = "") {
        action = nextAction
        keyword = ""
        scanQty = if (nextAction == InventoryAction.LOT_REGISTER) "" else "1"
        results = emptyList()
        selected = null
        qrData = null
        showLotDetail = false
        completion = null
        loading = false
        message = completionMessage
        setAllocations = emptyList()
        setActiveComponent = SetComponent.PBA
        setActiveGrade = ""
        setReview = false
        setSubmitting = false
        setMessage = ""
        setCompletion = null
        lastSetAllocation = null
        setRemarkOption = ""
        setCustomRemark = ""
    }

    fun selectAction(nextAction: InventoryAction) {
        if (action != nextAction) resetWork(nextAction)
    }

    fun loadHistory() {
        historyLoading = true
        historyMessage = ""
        scope.launch {
            val result = withContext(Dispatchers.IO) { ApiClient.history() }
            historyLoading = false
            if (result.error != null) {
                historyMessage = result.error
                if (result.error.contains("로그인이 만료")) onSessionExpired()
            } else {
                history = result.value.orEmpty()
                historyMessage = if (history.isEmpty()) "아직 처리 이력이 없습니다." else ""
            }
        }
    }

    LaunchedEffect("initial-history") {
        loadHistory()
    }

    fun search(itemCodeOverride: String? = null) {
        loading = true
        message = ""
        scope.launch {
            val result = withContext(Dispatchers.IO) {
                ApiClient.searchItems(
                    keyword = keyword.trim(),
                    warehouseType = warehouse.trim(),
                    itemCode = itemCodeOverride ?: qrData?.itemCode.orEmpty(),
                    lot = if (itemCodeOverride != null) qrData?.lot.orEmpty() else "",
                )
            }
            loading = false
            if (result.error != null) {
                message = result.error
                if (result.error.contains("로그인이 만료")) onSessionExpired()
            } else {
                results = result.value.orEmpty()
                message = if (results.isEmpty()) "검색 결과가 없습니다." else "${results.size}건을 찾았습니다."
                if (itemCodeOverride != null && results.size == 1) {
                    selected = results.first()
                    showLotDetail = false
                }
            }
        }
    }

    fun handleSetQr(parsed: QrMaterialData, report: (Boolean, String) -> Unit) {
        val target = setTargetText.toIntOrNull() ?: 0
        if (target <= 0) {
            setMessage = "출고 세트 수량을 먼저 입력하세요."
            report(false, setMessage)
            return
        }
        if (parsed.lot.isBlank()) {
            setMessage = "세트 출고는 LOT가 포함된 QR이 필요합니다."
            report(false, setMessage)
            return
        }
        if (setActiveGrade.isBlank()) {
            setMessage = "QR 인식 실패 · 출고할 등급(A/B/F)을 먼저 선택하세요."
            report(false, setMessage)
            return
        }
        setMessage = "QR 품목과 LOT 재고를 확인하고 있습니다."
        scope.launch {
            val result = withContext(Dispatchers.IO) {
                ApiClient.searchItems(
                    keyword = "",
                    warehouseType = warehouse,
                    itemCode = parsed.itemCode,
                    lot = parsed.lot,
                )
            }
            if (result.error != null) {
                setMessage = result.error
                report(false, setMessage)
                if (result.error.contains("로그인이 만료")) onSessionExpired()
                return@launch
            }
            val item = result.value.orEmpty().firstOrNull { it.grade == setActiveGrade }
            if (item == null) {
                setMessage = "QR과 일치하는 ${setActiveGrade}등급 재고를 찾지 못했습니다."
                report(false, setMessage)
                return@launch
            }
            val detected = detectSetComponent(item.itemName, parsed.itemName)
            if (detected == null) {
                setMessage = "QR 인식 실패 · 자재 유형을 확인할 수 없습니다.\nPBA, OUTER, INNER, TOP COVER QR만 사용할 수 있습니다."
                report(false, setMessage)
                return@launch
            }
            if (detected != setActiveComponent) {
                setMessage = "QR 인식 실패 · 자재명 불일치\n선택: ${setActiveComponent.label} / 스캔: ${detected.label}"
                report(false, setMessage)
                return@launch
            }
            if (setAllocations.any { it.item.id == item.id && it.qrData.lot == parsed.lot }) {
                setMessage = "이미 추가된 LOT입니다: ${parsed.lot}"
                report(false, setMessage)
                return@launch
            }
            val allocated = setAllocations.filter { it.component == detected }.sumOf { it.qty }
            val remaining = target - allocated
            if (remaining <= 0) {
                setMessage = "${detected.label}은 이미 목표 수량을 채웠습니다."
                report(false, setMessage)
                return@launch
            }
            // LOT가 있는 QR은 반드시 해당 LOT 잔량만 사용한다. LOT 잔량이 0일 때
            // 전체 품목 재고로 대체하면 실제로 없는 LOT가 배정되는 문제가 생긴다.
            val available = item.lotQty
            if (available <= 0) {
                setMessage = "LOT ${parsed.lot}은 출고 가능한 재고가 0 EA입니다. 다른 LOT를 스캔하세요."
                report(false, setMessage)
                return@launch
            }
            val allocationQty = minOf(available, remaining)
            val newAllocation = SetAllocation(detected, item, parsed, allocationQty)
            val updatedAllocations = setAllocations + newAllocation
            setAllocations = updatedAllocations
            lastSetAllocation = newAllocation
            val newTotal = allocated + allocationQty
            setMessage = "${detected.label} · LOT ${parsed.lot}에서 ${allocationQty} EA를 배정했습니다."
            val remainingAfter = target - newTotal
            report(
                true,
                if (remainingAfter <= 0) {
                    "${detected.label} 목표 수량을 채웠습니다. 다음 자재를 선택해 주세요."
                } else {
                    "LOT ${parsed.lot}에서 ${allocationQty} EA 배정 완료 · ${remainingAfter} EA가 더 필요합니다."
                },
            )
            val allComponentsReady = SetComponent.entries.all { component ->
                updatedAllocations.filter { it.component == component }.sumOf { it.qty } == target
            }
            if (allComponentsReady) {
                showScanner = false
                setMessage = ""
                setReview = true
                return@launch
            }
            if (newTotal >= target) {
                setActiveComponent = SetComponent.entries.firstOrNull { component ->
                    updatedAllocations.filter { it.component == component }.sumOf { it.qty } < target
                } ?: detected
            }
        }
    }

    BackHandler {
        when {
            showExitDialog -> showExitDialog = false
            showScanner -> showScanner = false
            setReview -> setReview = false
            setCompletion != null -> setCompletion = null
            completion != null -> completion = null
            selected != null -> selected = null
            mainTab == MainTab.WORK && action != null -> resetWork(null)
            mainTab != MainTab.HOME -> {
                mainTab = MainTab.HOME
            }
            else -> showExitDialog = true
        }
    }

    if (showExitDialog) {
        val activity = LocalContext.current as? Activity
        AlertDialog(
            onDismissRequest = { showExitDialog = false },
            title = { Text("앱을 종료할까요?") },
            text = { Text("진행 중인 작업은 없습니다. 종료하려면 확인을 눌러 주세요.") },
            dismissButton = {
                OutlinedButton(onClick = { showExitDialog = false }) { Text("취소") }
            },
            confirmButton = {
                Button(onClick = { activity?.finish() }) { Text("종료") }
            },
        )
    }

    if (showScanner) {
        val setTarget = setTargetText.toIntOrNull() ?: 0
        val setCurrent = setAllocations.filter { it.component == setActiveComponent }.sumOf { it.qty }
        LiveScannerScreen(
            onBack = { showScanner = false },
            setComponent = if (action == InventoryAction.SET_OUT) setActiveComponent else null,
            setProgress = if (action == InventoryAction.SET_OUT) "$setCurrent / $setTarget EA" else "",
            setGrade = if (action == InventoryAction.SET_OUT) setActiveGrade else "",
            onSetGradeChange = if (action == InventoryAction.SET_OUT) {
                { grade -> setActiveGrade = grade }
            } else null,
            onSetComponentChange = if (action == InventoryAction.SET_OUT) {
                { component -> setActiveComponent = component }
            } else null,
            onSetUse = if (action == InventoryAction.SET_OUT) {
                { parsed, report -> handleSetQr(parsed, report) }
            } else null,
            onUndoSetUse = if (action == InventoryAction.SET_OUT) {
                {
                    lastSetAllocation?.let { allocation ->
                        setAllocations = setAllocations - allocation
                        setActiveComponent = allocation.component
                        setMessage = "LOT ${allocation.qrData.lot} 배정을 취소했습니다."
                    }
                    lastSetAllocation = null
                }
            } else null,
            onUse = { parsed, detectedQty ->
                if (action != InventoryAction.SET_OUT) {
                    qrData = parsed
                    keyword = parsed.itemCode
                    scanQty = if (detectedQty > 0) detectedQty.toString() else ""
                    mainTab = MainTab.WORK
                    results = emptyList()
                    message = "QR 정보를 확인했습니다. 품목을 자동으로 조회합니다."
                    showScanner = false
                    search(parsed.itemCode)
                }
            },
        )
        return
    }

    if (setCompletion != null) {
        val done = setCompletion!!
        SetOutboundCompletionScreen(
            result = done,
            onNext = { resetWork(InventoryAction.SET_OUT) },
            onHistory = {
                resetWork(null)
                mainTab = MainTab.HISTORY
                loadHistory()
            },
        )
        return
    }

    if (completion != null) {
        val done = completion!!
        CompletionScreen(
            data = done,
            onNextScan = {
                resetWork()
                openScanner()
            },
            onSameLot = {
                selected = done.item.copy(
                    qty = done.result.afterQty,
                    lotQty = done.result.lotAfterQty,
                )
                qrData = done.qrData
                scanQty = if (done.action == InventoryAction.LOT_REGISTER) "" else "1"
                completion = null
                showLotDetail = false
            },
            onHistory = {
                resetWork()
                mainTab = MainTab.HISTORY
                loadHistory()
            },
            onHome = {
                resetWork()
                mainTab = MainTab.HOME
            },
        )
        return
    }

    if (selected != null && action != null) {
        if (showLotDetail) {
            LotDetailScreen(
                item = selected!!,
                qrData = qrData,
                onBack = {
                    showLotDetail = false
                    selected = null
                },
                onAction = {
                    action = it
                    showLotDetail = false
                },
            )
            return
        }
        MovementScreen(
            item = selected!!,
            initialQty = scanQty,
            action = action!!,
            qrData = qrData,
            onBack = { selected = null },
            onCompleted = { result, quantity ->
                completion = CompletionData(action!!, selected!!, quantity, result, qrData)
            },
            onSessionExpired = onSessionExpired,
        )
        return
    }

    Scaffold(
        containerColor = HermesBackground,
        bottomBar = {
            NavigationBar(containerColor = Color.White) {
                NavigationBarItem(
                    selected = mainTab == MainTab.HOME,
                    onClick = { mainTab = MainTab.HOME },
                    icon = { Icon(Icons.Filled.Home, contentDescription = null) },
                    label = { Text("홈") },
                )
                NavigationBarItem(
                    selected = mainTab == MainTab.WORK,
                    onClick = { mainTab = MainTab.WORK },
                    icon = { Icon(Icons.Filled.Inventory2, contentDescription = null) },
                    label = { Text("재고 처리") },
                )
                NavigationBarItem(
                    selected = mainTab == MainTab.HISTORY,
                    onClick = {
                        mainTab = MainTab.HISTORY
                        loadHistory()
                    },
                    icon = { Icon(Icons.Filled.History, contentDescription = null) },
                    label = { Text("이력") },
                )
                NavigationBarItem(
                    selected = mainTab == MainTab.PROFILE,
                    onClick = { mainTab = MainTab.PROFILE },
                    icon = { Icon(Icons.Filled.Person, contentDescription = null) },
                    label = { Text("내 정보") },
                )
            }
        },
    ) { scaffoldPadding ->
        when (mainTab) {
            MainTab.HOME -> HomeDashboard(
                modifier = Modifier.padding(scaffoldPadding),
                userId = currentUser,
                history = history,
                onScan = {
                    resetWork(null)
                    mainTab = MainTab.WORK
                },
            )
            MainTab.PROFILE -> ProfileScreen(
                modifier = Modifier.padding(scaffoldPadding),
                userId = currentUser,
                onLogout = onLogout,
            )
            MainTab.HISTORY -> HistoryScreen(
                modifier = Modifier.padding(scaffoldPadding),
                items = history,
                loading = historyLoading,
                message = historyMessage,
                userId = currentUser,
                onRefresh = { loadHistory() },
            )
            MainTab.WORK -> {
                if (action == null) {
                    ActionSelectionScreen(
                        modifier = Modifier.padding(scaffoldPadding),
                        onSelect = { selectAction(it) },
                    )
                } else if (action == InventoryAction.SET_OUT) {
                    SetOutboundScreen(
                        modifier = Modifier.padding(scaffoldPadding),
                        targetText = setTargetText,
                        onTargetChange = {
                            if (setAllocations.isEmpty()) setTargetText = it.filter(Char::isDigit)
                        },
                        activeComponent = setActiveComponent,
                        onComponentChange = { setActiveComponent = it },
                        allocations = setAllocations,
                        remarkOption = setRemarkOption,
                        customRemark = setCustomRemark,
                        onRemarkOptionChange = {
                            setRemarkOption = it
                            if (it != "직접 입력") setCustomRemark = ""
                        },
                        onCustomRemarkChange = { setCustomRemark = it },
                        message = setMessage,
                        review = setReview,
                        submitting = setSubmitting,
                        onScan = { openScanner() },
                        onRemove = { allocation ->
                            setAllocations = setAllocations - allocation
                            setMessage = "LOT ${allocation.qrData.lot} 배정을 삭제했습니다."
                        },
                        onReview = {
                            setMessage = ""
                            setReview = true
                        },
                        onBackFromReview = { setReview = false },
                        onChangeAction = { resetWork(null) },
                        onConfirm = {
                            val target = setTargetText.toIntOrNull() ?: 0
                            if (target > 0) {
                                setSubmitting = true
                                setMessage = "모든 LOT 재고를 다시 확인하고 있습니다."
                                val requestId = UUID.randomUUID().toString()
                                scope.launch {
                                    val result = withContext(Dispatchers.IO) {
                                        ApiClient.setMoveOut(
                                            setName = "QR 구성 세트",
                                            targetSets = target,
                                            requestId = requestId,
                                            remark = if (setRemarkOption == "직접 입력") setCustomRemark.trim() else setRemarkOption,
                                            lines = setAllocations.map { allocation ->
                                                SetOutboundLine(
                                                    inventoryId = allocation.item.id,
                                                    component = allocation.component.apiValue,
                                                    lot = allocation.qrData.lot,
                                                    qty = allocation.qty,
                                                )
                                            },
                                        )
                                    }
                                    setSubmitting = false
                                    if (result.error != null) {
                                        setMessage = result.error
                                        if (result.error.contains("로그인이 만료")) onSessionExpired()
                                    } else {
                                        setCompletion = result.value
                                    }
                                }
                            }
                        },
                    )
                } else {
                    WorkEntryScreen(
                        modifier = Modifier.padding(scaffoldPadding),
                        action = action!!,
                        warehouse = warehouse,
                        onWarehouseChange = { warehouse = it },
                        keyword = keyword,
                        onKeywordChange = {
                            keyword = it
                            qrData = null
                        },
                        results = results,
                        loading = loading,
                        message = message,
                        onChangeAction = { resetWork(null) },
                        onScan = { openScanner() },
                        onSearch = { search() },
                        onSelectItem = { selected = it },
                    )
                }
            }
        }
    }
}

@Composable
private fun ActionSelectionScreen(
    modifier: Modifier = Modifier,
    onSelect: (InventoryAction) -> Unit,
) {
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 18.dp, vertical = 16.dp)
    ) {
        Text("작업 선택", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("수행할 재고 작업을 선택하세요.", color = HermesTextMuted)
        Spacer(Modifier.height(20.dp))
        InventoryActionCard(
            title = "입고",
            description = "도착한 품목의 재고를 증가시킵니다.",
            icon = Icons.Filled.AddBox,
            background = Color(0xFFE0F4EE),
            accent = HermesGreen,
        ) { onSelect(InventoryAction.IN) }
        Spacer(Modifier.height(10.dp))
        InventoryActionCard(
            title = "출고",
            description = "선택한 LOT와 전체 재고를 차감합니다.",
            icon = Icons.Filled.IndeterminateCheckBox,
            background = Color(0xFFFFEAE4),
            accent = Color(0xFFB34B2D),
        ) { onSelect(InventoryAction.OUT) }
        Spacer(Modifier.height(10.dp))
        InventoryActionCard(
            title = "세트 출고",
            description = "PBA·OUTER·INNER·TOP COVER의 여러 LOT를 함께 출고합니다.",
            icon = Icons.Filled.Inventory2,
            background = Color(0xFFE0F4EE),
            accent = HermesGreen,
        ) { onSelect(InventoryAction.SET_OUT) }
        Spacer(Modifier.height(10.dp))
        InventoryActionCard(
            title = "LOT 등록",
            description = "새 LOT 정보를 등록하고 필요 시 입고합니다.",
            icon = Icons.Filled.LocalOffer,
            background = Color(0xFFEDEEFF),
            accent = Color(0xFF4C5DB6),
        ) { onSelect(InventoryAction.LOT_REGISTER) }
    }
}

@Composable
private fun InventoryActionCard(
    title: String,
    description: String,
    icon: ImageVector,
    background: Color,
    accent: Color,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick).border(1.dp, accent.copy(alpha = 0.18f), RoundedCornerShape(22.dp)),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = background.copy(alpha = 0.56f)),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.size(54.dp).clip(RoundedCornerShape(17.dp)).background(background),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, contentDescription = null, tint = accent)
            }
            Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(description, color = Color(0xFF61716F))
            }
            Box(Modifier.size(36.dp).clip(RoundedCornerShape(18.dp)).background(accent.copy(alpha = 0.13f)), contentAlignment = Alignment.Center) {
                Text("›", color = accent, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun WorkEntryScreen(
    modifier: Modifier = Modifier,
    action: InventoryAction,
    warehouse: String,
    onWarehouseChange: (String) -> Unit,
    keyword: String,
    onKeywordChange: (String) -> Unit,
    results: List<InventoryItem>,
    loading: Boolean,
    message: String,
    onChangeAction: () -> Unit,
    onScan: () -> Unit,
    onSearch: () -> Unit,
    onSelectItem: (InventoryItem) -> Unit,
) {
    var warehouseExpanded by remember { mutableStateOf(false) }
    val actionLabel = when (action) {
        InventoryAction.IN -> "입고"
        InventoryAction.OUT -> "출고"
        InventoryAction.LOT_REGISTER -> "LOT 등록"
        InventoryAction.SET_OUT -> "세트 출고"
    }
    val actionAccent = when (action) {
        InventoryAction.IN -> HermesGreen
        InventoryAction.OUT -> Color(0xFFB34B2D)
        InventoryAction.LOT_REGISTER -> Color(0xFF4C5DB6)
        InventoryAction.SET_OUT -> HermesGreen
    }

    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(16.dp)
    ) {
        Text(actionLabel, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("QR을 스캔하거나 품목을 검색하세요.", color = Color(0xFF61716F))
        Spacer(Modifier.height(14.dp))
        Card(
            colors = CardDefaults.cardColors(containerColor = actionAccent.copy(alpha = 0.12f)),
            shape = RoundedCornerShape(16.dp),
        ) {
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("$actionLabel 작업 중", color = actionAccent, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                OutlinedButton(onClick = onChangeAction) { Text("작업 변경") }
            }
        }
        Spacer(Modifier.height(14.dp))
        Text("창고 유형", color = Color(0xFF61716F))
        Box {
            Card(
                modifier = Modifier.fillMaxWidth().clickable { warehouseExpanded = true },
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
            ) {
                Row(
                    Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(warehouse, fontWeight = FontWeight.Bold)
                    Icon(Icons.Filled.KeyboardArrowDown, contentDescription = "창고 유형 선택")
                }
            }
            DropdownMenu(
                expanded = warehouseExpanded,
                onDismissRequest = { warehouseExpanded = false },
            ) {
                listOf("창고재고", "제공재고", "외주재고").forEach { option ->
                    DropdownMenuItem(
                        text = { Text(option) },
                        onClick = {
                            onWarehouseChange(option)
                            warehouseExpanded = false
                        },
                    )
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        Card(
            colors = CardDefaults.cardColors(containerColor = HermesNavy),
            shape = RoundedCornerShape(20.dp),
        ) {
            Column(Modifier.fillMaxWidth().padding(18.dp)) {
                Icon(Icons.Filled.QrCodeScanner, contentDescription = null, tint = HermesMint, modifier = Modifier.size(32.dp))
                Spacer(Modifier.height(10.dp))
                Text("QR을 스캔해 주세요", color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text("품목코드와 LOT를 읽어 자동으로 재고를 조회합니다.", color = Color(0xFFC8D7D5))
                Spacer(Modifier.height(14.dp))
                Button(onClick = onScan, modifier = Modifier.fillMaxWidth()) { Text("카메라 열기") }
            }
        }
        Spacer(Modifier.height(14.dp))
        Text("QR이 없나요?", fontWeight = FontWeight.Bold)
        OutlinedTextField(
            value = keyword,
            onValueChange = onKeywordChange,
            label = { Text("품목코드 또는 품목명") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Button(onClick = onSearch, enabled = !loading && keyword.isNotBlank(), modifier = Modifier.fillMaxWidth()) {
            Text("품목 검색")
        }
        if (loading) CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally).padding(12.dp))
        if (message.isNotBlank()) Text(message, modifier = Modifier.padding(vertical = 8.dp), color = Color(0xFF61716F))
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            results.forEach { item ->
                Card(
                    modifier = Modifier.fillMaxWidth().clickable { onSelectItem(item) },
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    shape = RoundedCornerShape(18.dp),
                ) {
                    Column(Modifier.fillMaxWidth().padding(16.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Text(item.itemCode, color = actionAccent, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                            Text(
                                "${item.grade.ifBlank { "-" }} 등급",
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.clip(RoundedCornerShape(999.dp)).background(actionAccent).padding(horizontal = 11.dp, vertical = 5.dp),
                            )
                        }
                        Text(item.itemName, style = MaterialTheme.typography.titleMedium)
                        Text("${item.warehouseType} · ${item.grade.ifBlank { "등급 없음" }} · 현재 재고 ${item.qty} EA", color = Color(0xFF61716F))
                        if (item.lot.isNotBlank()) Text("LOT ${item.lot}", color = Color(0xFF61716F))
                    }
                }
            }
        }
        Spacer(Modifier.height(18.dp))
    }
}

@Composable
private fun HistoryScreen(
    modifier: Modifier = Modifier,
    items: List<InventoryHistoryItem>,
    loading: Boolean,
    message: String,
    userId: String,
    onRefresh: () -> Unit,
) {
    var filter by rememberSaveable { mutableStateOf("전체") }
    fun isLotRegistration(item: InventoryHistoryItem): Boolean =
        item.movementType == "LOT_REGISTER" || item.source.contains("LOT", ignoreCase = true)
    val filteredItems = items.filter { item ->
        when (filter) {
            "입고" -> item.movementType == "IN" && !isLotRegistration(item)
            "출고" -> item.movementType == "OUT"
            "LOT" -> isLotRegistration(item)
            else -> true
        }
    }
    val inboundCount = items.count { it.movementType == "IN" && !isLotRegistration(it) }
    val outboundCount = items.count { it.movementType == "OUT" }
    val lotCount = items.count(::isLotRegistration)

    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 18.dp, vertical = 16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("처리 이력", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                Text("최근 재고 작업을 한눈에 확인하세요.", color = HermesTextMuted)
            }
            IconButton(onClick = onRefresh, enabled = !loading) {
                Icon(Icons.Filled.History, contentDescription = "처리 이력 새로고침", tint = HermesGreen)
            }
        }
        Spacer(Modifier.height(14.dp))
        Card(
            colors = CardDefaults.cardColors(containerColor = HermesNavy),
            shape = RoundedCornerShape(22.dp),
        ) {
            Column(Modifier.fillMaxWidth().padding(18.dp)) {
                Text("현재 로그인 계정", color = Color(0xFFAFC6C1))
                Text(userId, color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(14.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    HistoryStat("입고", inboundCount, HermesMint, Modifier.weight(1f))
                    HistoryStat("출고", outboundCount, Color(0xFFFFA58E), Modifier.weight(1f))
                    HistoryStat("LOT", lotCount, Color(0xFFB9C2FF), Modifier.weight(1f))
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
            listOf("전체", "입고", "출고", "LOT").forEach { option ->
                if (filter == option) {
                    Button(onClick = { filter = option }, modifier = Modifier.weight(1f)) { Text(option) }
                } else {
                    OutlinedButton(onClick = { filter = option }, modifier = Modifier.weight(1f)) { Text(option) }
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        if (loading) {
            CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally).padding(24.dp))
        } else if (message.isNotBlank()) {
            Text(message, modifier = Modifier.padding(vertical = 20.dp), color = HermesTextMuted)
        }
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            filteredItems.forEach { item ->
                val lotRegistration = isLotRegistration(item)
                val setOutbound = item.requestId.isNotBlank()
                val inbound = item.movementType == "IN" && !lotRegistration
                val accent = when {
                    lotRegistration -> HermesPurple
                    setOutbound -> HermesGreen
                    inbound -> HermesGreen
                    else -> HermesOrange
                }
                val label = when {
                    lotRegistration -> "LOT 등록"
                    setOutbound -> "세트 출고"
                    inbound -> "입고"
                    else -> "출고"
                }
                val quantityPrefix = if (inbound || lotRegistration) "+" else "−"
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                ) {
                    Column(Modifier.fillMaxWidth().padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                label,
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.clip(RoundedCornerShape(999.dp)).background(accent)
                                    .padding(horizontal = 10.dp, vertical = 4.dp),
                            )
                            Text(item.createdAt, color = HermesTextMuted, modifier = Modifier.padding(start = 10.dp), style = MaterialTheme.typography.bodySmall)
                            Spacer(Modifier.weight(1f))
                            Text("$quantityPrefix${item.qty} EA", color = accent, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        }
                        Spacer(Modifier.height(10.dp))
                        Text(item.itemCode, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                        Text(item.itemName)
                        Spacer(Modifier.height(6.dp))
                        Text("${item.warehouseType} · ${item.grade.ifBlank { "-" }}등급 · LOT ${item.lot.ifBlank { "-" }}", color = HermesTextMuted)
                        if (setOutbound) Text("${item.setComponent} · ${item.setCount} SET", color = HermesGreen, style = MaterialTheme.typography.bodySmall)
                        Text("작업자 $userId", color = HermesTextMuted, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
        if (!loading && filteredItems.isEmpty() && message.isBlank()) {
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F1EF))) {
                Text("선택한 조건의 처리 이력이 없습니다.", modifier = Modifier.fillMaxWidth().padding(18.dp), color = HermesTextMuted)
            }
        }
        Spacer(Modifier.height(14.dp))
        Text(
            "잘못 처리한 기록은 삭제하지 말고 관리자 확인 후 반대 거래로 정정하세요.",
            color = Color(0xFF8A5A00),
            style = MaterialTheme.typography.bodySmall,
        )
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun HistoryStat(label: String, count: Int, accent: Color, modifier: Modifier = Modifier) {
    Column(
        modifier
            .clip(RoundedCornerShape(14.dp))
            .background(Color(0xFF183E41))
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        Text(label, color = Color(0xFFAFC6C1), style = MaterialTheme.typography.bodySmall)
        Text(count.toString(), color = accent, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun LotDetailScreen(
    item: InventoryItem,
    qrData: QrMaterialData?,
    onBack: () -> Unit,
    onAction: (InventoryAction) -> Unit,
) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)
    ) {
        OutlinedButton(onClick = onBack) { Text("← 다시 스캔") }
        Spacer(Modifier.height(18.dp))
        Text("LOT 상세 정보", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("QR 정보와 웹 재고를 확인한 뒤 작업을 선택하세요.", color = Color(0xFF61716F))
        Spacer(Modifier.height(16.dp))
        Card(
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
        ) {
            Column(Modifier.fillMaxWidth().padding(20.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = HermesGreen)
                    Text("QR 정보 확인됨", color = HermesGreen, fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 8.dp))
                }
                Spacer(Modifier.height(14.dp))
                Text(item.itemCode, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(item.itemName, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(14.dp))
                ProfileInfoRow("LOT", qrData?.lot.orEmpty().ifBlank { "-" })
                ProfileInfoRow("최초 입고일자", qrData?.receivedDate.orEmpty().ifBlank { "-" })
                ProfileInfoRow("검사원", qrData?.inspector.orEmpty().ifBlank { "-" })
                ProfileInfoRow("창고 / 등급", "${item.warehouseType} / ${item.grade.ifBlank { "-" }}")
            }
        }
        Spacer(Modifier.height(14.dp))
        Card(
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFE7F6F1)),
        ) {
            Column(Modifier.fillMaxWidth().padding(20.dp)) {
                Text("현재 재고", color = HermesGreen, fontWeight = FontWeight.Bold)
                Text("전체 ${item.qty} EA", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                if (!qrData?.lot.isNullOrBlank()) {
                    Text("해당 LOT ${item.lotQty} EA", style = MaterialTheme.typography.titleMedium)
                }
            }
        }
        Spacer(Modifier.height(20.dp))
        Text("작업 선택", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(10.dp))
        Button(onClick = { onAction(InventoryAction.IN) }, modifier = Modifier.fillMaxWidth()) { Text("입고 처리") }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = { onAction(InventoryAction.OUT) }, modifier = Modifier.fillMaxWidth()) { Text("출고 처리") }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = { onAction(InventoryAction.LOT_REGISTER) }, modifier = Modifier.fillMaxWidth()) { Text("LOT 등록") }
    }
}

@Composable
private fun SetOutboundScreen(
    modifier: Modifier = Modifier,
    targetText: String,
    onTargetChange: (String) -> Unit,
    activeComponent: SetComponent,
    onComponentChange: (SetComponent) -> Unit,
    allocations: List<SetAllocation>,
    remarkOption: String,
    customRemark: String,
    onRemarkOptionChange: (String) -> Unit,
    onCustomRemarkChange: (String) -> Unit,
    message: String,
    review: Boolean,
    submitting: Boolean,
    onScan: () -> Unit,
    onRemove: (SetAllocation) -> Unit,
    onReview: () -> Unit,
    onBackFromReview: () -> Unit,
    onChangeAction: () -> Unit,
    onConfirm: () -> Unit,
) {
    var remarkExpanded by remember { mutableStateOf(false) }
    val target = targetText.toIntOrNull() ?: 0
    fun total(component: SetComponent) = allocations.filter { it.component == component }.sumOf { it.qty }
    val allReady = target > 0 && SetComponent.entries.all { total(it) == target }
    val finalRemark = if (remarkOption == "직접 입력") customRemark.trim() else remarkOption

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedButton(onClick = if (review) onBackFromReview else onChangeAction) { Text("← 이전") }
            Column(Modifier.padding(start = 12.dp)) {
                Text(if (review) "FINAL CHECK" else "SET OUTBOUND", color = HermesGreen, fontWeight = FontWeight.Bold)
                Text(if (review) "세트 출고 최종 확인" else "다중 LOT 세트 출고", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            }
        }
        Spacer(Modifier.height(14.dp))

        if (review) {
            Card(colors = CardDefaults.cardColors(containerColor = HermesNavy), shape = RoundedCornerShape(22.dp)) {
                Column(Modifier.fillMaxWidth().padding(18.dp)) {
                    Text("출고 전 마지막 확인", color = HermesMint, fontWeight = FontWeight.Bold)
                    Text("$target SET", color = Color.White, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                    Text("4개 자재 · ${allocations.size}개 LOT · 총 ${target * SetComponent.entries.size} EA", color = Color(0xFFC8D7D5))
                    Text("비고 · ${finalRemark.ifBlank { "미선택" }}", color = Color(0xFFC8D7D5), modifier = Modifier.padding(top = 4.dp))
                }
            }
            Spacer(Modifier.height(12.dp))
            if (message.isNotBlank()) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEAE4)),
                    shape = RoundedCornerShape(18.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(Modifier.fillMaxWidth().padding(16.dp)) {
                        Text("출고할 수 없습니다", color = HermesOrange, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                        Spacer(Modifier.height(4.dp))
                        Text(message, fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.height(6.dp))
                        Text("← 이전을 눌러 문제가 있는 LOT를 삭제한 뒤 다른 LOT를 스캔하세요.", color = HermesTextMuted, style = MaterialTheme.typography.bodySmall)
                    }
                }
                Spacer(Modifier.height(12.dp))
            }
            Text("구성품 완료 상태", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            SetComponent.entries.chunked(2).forEach { components ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    components.forEach { component ->
                        val componentLots = allocations.filter { it.component == component }
                        val accent = setComponentColor(component)
                        Card(
                            colors = CardDefaults.cardColors(containerColor = accent.copy(alpha = 0.10f)),
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.weight(1f).border(1.dp, accent.copy(alpha = 0.35f), RoundedCornerShape(16.dp)),
                        ) {
                            Column(Modifier.fillMaxWidth().padding(12.dp)) {
                                Text("✓ ${component.label}", color = accent, fontWeight = FontWeight.Bold)
                                Text("${total(component)} / $target EA", fontWeight = FontWeight.Bold)
                                Text("${componentLots.size}개 LOT", color = HermesTextMuted, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
            }
            Spacer(Modifier.height(6.dp))
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF4DE)), shape = RoundedCornerShape(16.dp)) {
                Text("아래 LOT 번호와 수량을 실제 자재와 대조해 주세요.", color = Color(0xFF795500), fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth().padding(14.dp))
            }
            Spacer(Modifier.height(14.dp))
            Text("LOT 상세 검토", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            SetComponent.entries.forEach { component ->
                val accent = setComponentColor(component)
                val componentAllocations = allocations.filter { it.component == component }
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    shape = RoundedCornerShape(20.dp),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp).border(2.dp, accent.copy(alpha = 0.45f), RoundedCornerShape(20.dp)),
                ) {
                    Column(Modifier.fillMaxWidth().padding(16.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(component.label, color = accent, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                            Text("${total(component)} EA ✓", color = accent, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                        }
                        componentAllocations.forEachIndexed { index, allocation ->
                            Spacer(Modifier.height(10.dp))
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                                Box(Modifier.size(30.dp).clip(RoundedCornerShape(10.dp)).background(accent.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {
                                    Text("${index + 1}", color = accent, fontWeight = FontWeight.Bold)
                                }
                                Column(Modifier.weight(1f)) {
                                    Text("LOT ${allocation.qrData.lot}", fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 10.dp))
                                    Text("${allocation.item.itemCode} · ${allocation.item.grade}등급", color = HermesTextMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 10.dp))
                                }
                                Text("${allocation.qty} EA", color = accent, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                            }
                        }
                    }
                }
            }
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFE7F6F1)), shape = RoundedCornerShape(16.dp)) {
                Text("확정 시 위 LOT가 한 번에 처리됩니다. 재고가 하나라도 부족하면 전체 출고가 취소됩니다.", color = HermesGreen, fontWeight = FontWeight.SemiBold, modifier = Modifier.fillMaxWidth().padding(14.dp))
            }
            Spacer(Modifier.height(14.dp))
            Button(onClick = onConfirm, enabled = !submitting && allReady, modifier = Modifier.fillMaxWidth()) {
                if (submitting) CircularProgressIndicator(Modifier.size(20.dp), color = Color.White) else Text("$target 세트 출고 확정")
            }
            if (submitting) Text(message, modifier = Modifier.padding(top = 12.dp), color = HermesGreen)
            return@Column
        }

        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(18.dp)) {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text("출고 목표", fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = targetText,
                    onValueChange = onTargetChange,
                    label = { Text("세트 수량") },
                    suffix = { Text("SET") },
                    supportingText = { Text(if (allocations.isEmpty()) "수량 입력 후 자재별 QR을 스캔하세요." else "스캔 시작 후에는 LOT를 모두 삭제해야 수량을 바꿀 수 있습니다.") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
        Spacer(Modifier.height(12.dp))
        Text("출고 구분", fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(6.dp))
        Box {
            Card(
                modifier = Modifier.fillMaxWidth().clickable { remarkExpanded = true }.border(1.dp, HermesOutline, RoundedCornerShape(14.dp)),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
            ) {
                Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text(remarkOption.ifBlank { "선택사항" }, color = if (remarkOption.isBlank()) HermesTextMuted else HermesNavy, fontWeight = if (remarkOption.isBlank()) FontWeight.Normal else FontWeight.Bold)
                    Icon(Icons.Filled.KeyboardArrowDown, contentDescription = "출고 구분 선택")
                }
            }
            DropdownMenu(expanded = remarkExpanded, onDismissRequest = { remarkExpanded = false }) {
                listOf("연구시료", "양산", "직접 입력").forEach { option ->
                    DropdownMenuItem(text = { Text(option) }, onClick = {
                        onRemarkOptionChange(option)
                        remarkExpanded = false
                    })
                }
            }
        }
        if (remarkOption == "직접 입력") {
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = customRemark,
                onValueChange = onCustomRemarkChange,
                label = { Text("비고 직접 입력") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        Spacer(Modifier.height(14.dp))
        Text("자재 선택", fontWeight = FontWeight.Bold)
        Text("스캔할 자재를 먼저 선택하세요.", color = HermesTextMuted, style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(8.dp))
        SetComponent.entries.chunked(2).forEach { rowItems ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                rowItems.forEach { component ->
                    val current = total(component)
                    val selected = component == activeComponent
                    val ready = target > 0 && current == target
                    if (selected) {
                        Button(onClick = { onComponentChange(component) }, modifier = Modifier.weight(1f)) {
                            Text("${if (ready) "✓ " else ""}${component.label}\n$current/$target")
                        }
                    } else {
                        OutlinedButton(onClick = { onComponentChange(component) }, modifier = Modifier.weight(1f)) {
                            Text("${if (ready) "✓ " else ""}${component.label}\n$current/$target")
                        }
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }

        val activeTotal = total(activeComponent)
        Card(colors = CardDefaults.cardColors(containerColor = HermesGreen.copy(alpha = 0.10f)), shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.fillMaxWidth().padding(18.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(Icons.Filled.QrCodeScanner, contentDescription = null, tint = HermesGreen, modifier = Modifier.size(38.dp))
                Spacer(Modifier.height(8.dp))
                Text("세트 QR 스캔", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(if (activeTotal >= target && target > 0) "${activeComponent.label} 완료 · 카메라에서 다른 자재를 선택할 수 있습니다." else "${activeComponent.label} 남은 수량 ${maxOf(target - activeTotal, 0)} EA", color = HermesTextMuted)
                Spacer(Modifier.height(12.dp))
                Button(onClick = onScan, enabled = target > 0 && !allReady, modifier = Modifier.fillMaxWidth()) { Text("QR 카메라 열기") }
            }
        }
        Spacer(Modifier.height(14.dp))
        Text("${activeComponent.label} 배정 LOT", fontWeight = FontWeight.Bold)
        val activeAllocations = allocations.filter { it.component == activeComponent }
        if (activeAllocations.isEmpty()) {
            Text("아직 스캔한 LOT가 없습니다.", color = HermesTextMuted, modifier = Modifier.padding(vertical = 14.dp))
        } else {
            activeAllocations.forEach { allocation ->
                Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
                    Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("LOT ${allocation.qrData.lot}", fontWeight = FontWeight.Bold)
                            Text("${allocation.item.itemCode} · ${allocation.item.grade}등급 · ${allocation.item.itemName}", color = HermesTextMuted, style = MaterialTheme.typography.bodySmall)
                        }
                        Text("${allocation.qty} EA", fontWeight = FontWeight.Bold, color = HermesGreen)
                        IconButton(onClick = { onRemove(allocation) }) { Text("×", style = MaterialTheme.typography.headlineSmall, color = HermesOrange) }
                    }
                }
            }
        }
        if (message.isNotBlank()) {
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF4DE)), shape = RoundedCornerShape(14.dp), modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp)) {
                Text(message, color = Color(0xFF795500), fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(12.dp))
            }
        }
        Spacer(Modifier.height(8.dp))
        Button(onClick = onReview, enabled = allReady, modifier = Modifier.fillMaxWidth()) {
            Text(if (allReady) "전체 LOT 검토하기" else "4개 자재의 목표 수량을 채워 주세요")
        }
    }
}

@Composable
private fun SetOutboundCompletionScreen(
    result: SetOutboundResult,
    onNext: () -> Unit,
    onHistory: () -> Unit,
) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Spacer(Modifier.height(30.dp))
        Box(Modifier.size(82.dp).clip(RoundedCornerShape(41.dp)).background(HermesGreen.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {
            Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = HermesGreen, modifier = Modifier.size(58.dp))
        }
        Spacer(Modifier.height(14.dp))
        Text("세트 출고가 완료되었습니다", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text("모든 구성품과 LOT가 함께 처리되었습니다.", color = HermesTextMuted)
        Spacer(Modifier.height(22.dp))
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(22.dp)) {
            Column(Modifier.fillMaxWidth().padding(20.dp)) {
                ProfileInfoRow("출고 세트", "${result.targetSets} SET")
                ProfileInfoRow("처리 LOT", "${result.lineCount}개")
                ProfileInfoRow("총 출고 수량", "${result.totalQty} EA")
                ProfileInfoRow("작업자", ApiClient.currentUser())
                ProfileInfoRow("처리 번호", result.groupId.take(8).uppercase())
            }
        }
        Spacer(Modifier.height(20.dp))
        Button(onClick = onNext, modifier = Modifier.fillMaxWidth()) { Text("새 세트 출고") }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = onHistory, modifier = Modifier.fillMaxWidth()) { Text("처리 이력 보기") }
    }
}

@Composable
private fun CompletionScreen(
    data: CompletionData,
    onNextScan: () -> Unit,
    onSameLot: () -> Unit,
    onHistory: () -> Unit,
    onHome: () -> Unit,
) {
    val label = when (data.action) {
        InventoryAction.IN -> "입고"
        InventoryAction.OUT -> "출고"
        InventoryAction.LOT_REGISTER -> "LOT 등록"
        InventoryAction.SET_OUT -> "세트 출고"
    }
    val accent = when (data.action) {
        InventoryAction.IN -> HermesGreen
        InventoryAction.OUT -> HermesOrange
        InventoryAction.LOT_REGISTER -> HermesPurple
        InventoryAction.SET_OUT -> HermesGreen
    }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(24.dp))
        Box(Modifier.size(82.dp).clip(RoundedCornerShape(41.dp)).background(accent.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {
            Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = accent, modifier = Modifier.size(58.dp))
        }
        Spacer(Modifier.height(14.dp))
        Text("${label}이 완료되었습니다", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text("${data.item.itemCode} · ${data.item.itemName}", color = HermesTextMuted)
        Spacer(Modifier.height(22.dp))
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(22.dp)) {
            Column(Modifier.fillMaxWidth().padding(20.dp)) {
                Text("처리 결과", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                ProfileInfoRow("등급", data.item.grade.ifBlank { "-" })
                ProfileInfoRow("처리 수량", "${if (data.action == InventoryAction.OUT) "−" else "+"}${data.quantity} EA")
                ProfileInfoRow("전체 재고", "${data.result.beforeQty} → ${data.result.afterQty} EA")
                ProfileInfoRow("작업자", ApiClient.currentUser())
                if (data.result.lot.isNotBlank()) {
                    ProfileInfoRow("LOT", data.result.lot)
                    ProfileInfoRow("LOT 재고", "${data.result.lotBeforeQty} → ${data.result.lotAfterQty} EA")
                }
            }
        }
        Spacer(Modifier.height(20.dp))
        Button(onClick = onNextScan, modifier = Modifier.fillMaxWidth()) { Text("다음 QR 스캔") }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = onSameLot, modifier = Modifier.fillMaxWidth()) { Text("같은 LOT 계속 처리") }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = onHistory, modifier = Modifier.fillMaxWidth()) { Text("처리 이력 보기") }
        OutlinedButton(onClick = onHome, modifier = Modifier.fillMaxWidth()) { Text("홈으로") }
    }
}

@Composable
private fun HomeDashboard(
    modifier: Modifier = Modifier,
    userId: String,
    history: List<InventoryHistoryItem>,
    onScan: () -> Unit,
) {
    val inboundCount = history.count { it.movementType == "IN" }
    val outboundCount = history.count { it.movementType == "OUT" }
    val lotCount = history.count { it.movementType == "LOT_REGISTER" || it.source.contains("LOT", ignoreCase = true) }
    val setCount = history.map { it.requestId }.filter(String::isNotBlank).distinct().size
    val recentItems = history.take(4)
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 18.dp)
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(28.dp),
            colors = CardDefaults.cardColors(containerColor = HermesNavy),
        ) {
            Column(Modifier.padding(22.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("LOGISTICS SYSTEM", color = HermesMint, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelMedium)
                        Text("안녕하세요, ${userId}님", color = Color.White, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    }
                    if (BuildConfig.IS_DEV) {
                        Text("DEV", color = Color.White, fontWeight = FontWeight.Bold, modifier = Modifier.clip(RoundedCornerShape(999.dp)).background(Color(0xFFE17A22)).padding(horizontal = 10.dp, vertical = 4.dp))
                    }
                }
                Spacer(Modifier.height(22.dp))
                Card(
                    modifier = Modifier.fillMaxWidth().clickable(onClick = onScan),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = HermesGreen),
                ) {
                    Row(Modifier.fillMaxWidth().padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(52.dp).clip(RoundedCornerShape(16.dp)).background(Color.White.copy(alpha = 0.14f)), contentAlignment = Alignment.Center) {
                            Icon(Icons.Filled.QrCodeScanner, contentDescription = null, tint = Color.White, modifier = Modifier.size(30.dp))
                        }
                        Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                            Text("빠르고 정확한 작업", color = Color(0xFFD8F5ED), style = MaterialTheme.typography.bodySmall)
                            Text("QR 스캔 시작", color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        }
                        Box(Modifier.size(34.dp).clip(RoundedCornerShape(17.dp)).background(Color.White), contentAlignment = Alignment.Center) {
                            Text("›", color = HermesGreen, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
        Spacer(Modifier.height(22.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text("작업 현황", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("최근 50건", color = HermesTextMuted, style = MaterialTheme.typography.bodySmall)
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            HomeStat("입고", inboundCount, "↓", Color(0xFFE0F4EE), HermesGreen, Modifier.weight(1f))
            HomeStat("출고", outboundCount, "↑", Color(0xFFFFEAE4), HermesOrange, Modifier.weight(1f))
            HomeStat("세트", setCount, "□", Color(0xFFE8F1EF), HermesGreen, Modifier.weight(1f))
            HomeStat("LOT", lotCount, "L", Color(0xFFEDEEFF), HermesPurple, Modifier.weight(1f))
        }
        if (recentItems.isNotEmpty()) {
            Spacer(Modifier.height(20.dp))
            Text("최근 작업", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(10.dp))
            Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 6.dp)) {
                    recentItems.forEachIndexed { index, recent ->
                        val isOut = recent.movementType == "OUT"
                        Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                            Box(Modifier.size(36.dp).clip(RoundedCornerShape(12.dp)).background(if (isOut) Color(0xFFFFEAE4) else Color(0xFFE0F4EE)), contentAlignment = Alignment.Center) {
                                Text(if (isOut) "↑" else "↓", color = if (isOut) HermesOrange else HermesGreen, fontWeight = FontWeight.Bold)
                            }
                            Column(Modifier.weight(1f).padding(horizontal = 11.dp)) {
                                Text(recent.itemCode, fontWeight = FontWeight.Bold)
                                Text("${recent.itemName} · ${if (isOut) "출고" else "입고"}", color = HermesTextMuted, style = MaterialTheme.typography.bodySmall)
                            }
                            Text("${if (isOut) "−" else "+"}${recent.qty} EA", color = if (isOut) HermesOrange else HermesGreen, fontWeight = FontWeight.Bold)
                        }
                        if (index < recentItems.lastIndex) Box(Modifier.fillMaxWidth().height(1.dp).background(HermesOutline.copy(alpha = 0.6f)))
                    }
                }
            }
        }
    }
}

@Composable
private fun HomeStat(label: String, count: Int, symbol: String, background: Color, accent: Color, modifier: Modifier = Modifier) {
    Column(modifier.clip(RoundedCornerShape(16.dp)).background(Color.White).padding(vertical = 11.dp, horizontal = 4.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Box(Modifier.size(32.dp).clip(RoundedCornerShape(10.dp)).background(background), contentAlignment = Alignment.Center) {
            Text(symbol, color = accent, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
        }
        Spacer(Modifier.height(5.dp))
        Text(label, color = HermesTextMuted, style = MaterialTheme.typography.labelSmall)
        Text("$count", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ProductActionCard(
    title: String,
    description: String,
    background: Color,
    accent: Color,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = background),
    ) {
        Row(Modifier.fillMaxWidth().padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(42.dp).clip(RoundedCornerShape(13.dp)).background(accent), contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Inventory2, contentDescription = null, tint = Color.White)
            }
            Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                Text(title, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                Text(description, color = Color(0xFF61716F), style = MaterialTheme.typography.bodyMedium)
            }
            Text("›", color = accent, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun ProfileScreen(modifier: Modifier = Modifier, userId: String, onLogout: () -> Unit) {
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
        Text("내 정보", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("계정과 앱 정보를 확인하세요.", color = Color(0xFF61716F))
        Spacer(Modifier.height(18.dp))
        Card(shape = RoundedCornerShape(24.dp), colors = CardDefaults.cardColors(containerColor = HermesNavy)) {
            Row(Modifier.fillMaxWidth().padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(50.dp).clip(RoundedCornerShape(16.dp)).background(HermesGreen), contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.Person, contentDescription = null, tint = Color.White)
                }
                Column(Modifier.padding(start = 14.dp)) {
                    Text(userId, color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text("현재 로그인한 계정", color = Color(0xFFC8D7D5))
                }
            }
        }
        Spacer(Modifier.height(18.dp))
        Card(shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
            Column(Modifier.fillMaxWidth().padding(18.dp)) {
                Text("앱 정보", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(14.dp))
                ProfileInfoRow("앱 버전", BuildConfig.VERSION_NAME)
                ProfileInfoRow("환경", if (BuildConfig.IS_DEV) "DEV" else "PROD")
                ProfileInfoRow("QR 스캔", "인터넷 없이도 인식")
            }
        }
        Spacer(Modifier.height(14.dp))
        Card(shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
            Column(Modifier.fillMaxWidth().padding(18.dp)) {
                Text("작업 안내", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(10.dp))
                Text("• QR 인식 후 품목코드와 LOT를 확인하세요.")
                Text("• 수량과 등급을 확인한 뒤 최종 처리하세요.")
                Text("• 오류가 있으면 처리하지 말고 다시 스캔하세요.")
            }
        }
        Spacer(Modifier.height(22.dp))
        OutlinedButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) { Text("로그아웃") }
    }
}

@Composable
private fun ProfileInfoRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 7.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Color(0xFF70807D))
        Text(value, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun LiveScannerScreen(
    onBack: () -> Unit,
    setComponent: SetComponent? = null,
    setProgress: String = "",
    setGrade: String = "",
    onSetComponentChange: ((SetComponent) -> Unit)? = null,
    onSetGradeChange: ((String) -> Unit)? = null,
    onSetUse: ((QrMaterialData, (Boolean, String) -> Unit) -> Unit)? = null,
    onUndoSetUse: (() -> Unit)? = null,
    onUse: (QrMaterialData, Int) -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var candidate by remember { mutableStateOf("") }
    var parsed by remember { mutableStateOf(QrMaterialData()) }
    var rawText by remember { mutableStateOf("QR 코드를 화면 중앙에 맞춰 주세요.") }
    var validating by remember { mutableStateOf(false) }
    var feedbackSuccess by remember { mutableStateOf<Boolean?>(null) }
    var feedbackText by remember { mutableStateOf("") }
    val currentOnSetUse by rememberUpdatedState(onSetUse)
    val analyzing = remember { AtomicBoolean(false) }
    val locked = remember { AtomicBoolean(false) }
    val toneGenerator = remember { ToneGenerator(AudioManager.STREAM_MUSIC, 90) }
    val executor = remember { Executors.newSingleThreadExecutor() }
    val scanner = remember {
        BarcodeScanning.getClient(
            BarcodeScannerOptions.Builder()
                .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                .build()
        )
    }
    val controller = remember {
        LifecycleCameraController(context).apply {
            cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
        }
    }

    fun resetScan() {
        candidate = ""
        parsed = QrMaterialData()
        feedbackSuccess = null
        feedbackText = ""
        validating = false
        locked.set(false)
        rawText = "QR 코드를 화면 중앙에 맞춰 주세요."
    }

    DisposableEffect(lifecycleOwner) {
        controller.bindToLifecycle(lifecycleOwner)
        controller.setImageAnalysisAnalyzer(executor) { imageProxy ->
            if (!analyzing.compareAndSet(false, true)) {
                imageProxy.close()
                return@setImageAnalysisAnalyzer
            }
            val mediaImage = imageProxy.image
            if (mediaImage == null) {
                analyzing.set(false)
                imageProxy.close()
                return@setImageAnalysisAnalyzer
            }
            val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
            scanner.process(image)
                .addOnSuccessListener { barcodes ->
                    if (!locked.get()) {
                        val value = barcodes.firstNotNullOfOrNull { it.rawValue?.trim()?.takeIf(String::isNotBlank) }
                        if (value != null) {
                            val parsedValue = parseMaterialQr(value)
                            candidate = value
                            parsed = parsedValue
                            rawText = if (parsedValue.itemCode.isBlank()) {
                                "품목코드를 찾지 못했습니다. QR 형식을 확인해 주세요."
                            } else {
                                if (currentOnSetUse != null) "QR 인식 완료 · 자재와 재고를 자동 확인하고 있습니다." else "QR 인식 완료 · 품목코드로 매칭합니다."
                            }
                            locked.set(parsedValue.itemCode.isNotBlank())
                            if (parsedValue.itemCode.isNotBlank()) {
                                currentOnSetUse?.let { validateSetQr ->
                                    validating = true
                                    toneGenerator.startTone(ToneGenerator.TONE_PROP_BEEP, 90)
                                    validateSetQr(parsedValue) { success, text ->
                                        validating = false
                                        feedbackSuccess = success
                                        feedbackText = text
                                        toneGenerator.startTone(
                                            if (success) ToneGenerator.TONE_PROP_ACK else ToneGenerator.TONE_SUP_ERROR,
                                            if (success) 180 else 420,
                                        )
                                    }
                                } ?: toneGenerator.startTone(ToneGenerator.TONE_PROP_BEEP, 180)
                            }
                        }
                    }
                }
                .addOnCompleteListener {
                    analyzing.set(false)
                    imageProxy.close()
                }
        }
        onDispose {
            controller.clearImageAnalysisAnalyzer()
            controller.unbind()
            scanner.close()
            executor.shutdown()
            toneGenerator.release()
        }
    }

    Column(Modifier.fillMaxSize().background(Color.White)) {
        Box(Modifier.fillMaxWidth().weight(1f).background(Color.Black)) {
            AndroidView(
                factory = { PreviewView(it).apply { this.controller = controller } },
                modifier = Modifier.fillMaxSize(),
            )
            Box(
                modifier = Modifier
                    .align(Alignment.Center)
                    .fillMaxWidth(0.78f)
                    .height(220.dp)
                    .clip(RoundedCornerShape(28.dp))
                    .border(
                        width = if (parsed.itemCode.isNotBlank()) 5.dp else 2.dp,
                        brush = if (feedbackSuccess == false) {
                            Brush.linearGradient(listOf(Color(0xFFFF8A65), Color(0xFFBA1A1A)))
                        } else if (feedbackSuccess == true) {
                            Brush.linearGradient(listOf(Color(0xFF41F2B7), Color(0xFF00A77E), Color(0xFF9BFFD9)))
                        } else if (onSetUse != null && (validating || parsed.itemCode.isNotBlank())) {
                            Brush.linearGradient(listOf(Color(0xFFFFC857), Color(0xFFE17A22)))
                        } else if (parsed.itemCode.isNotBlank()) {
                            Brush.linearGradient(listOf(Color(0xFF41F2B7), Color(0xFF00A77E), Color(0xFF9BFFD9)))
                        } else {
                            Brush.linearGradient(listOf(Color(0xCCFFFFFF), Color(0x66FFFFFF)))
                        },
                        shape = RoundedCornerShape(28.dp),
                    )
            ) {
                if (parsed.itemCode.isNotBlank()) {
                    Row(
                        modifier = Modifier.align(Alignment.TopCenter).padding(top = 14.dp).clip(RoundedCornerShape(999.dp)).background(
                            when (feedbackSuccess) {
                                true -> Color(0xE6006C5B)
                                false -> Color(0xE6BA1A1A)
                                null -> if (onSetUse != null) Color(0xE6C66A10) else Color(0xE6006C5B)
                            }
                        ).padding(horizontal = 14.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        if (feedbackSuccess == true) Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                        Text(
                            when (feedbackSuccess) {
                                true -> "배정 완료"
                                false -> "QR 인식 실패"
                                null -> if (validating) "재고 확인 중" else "QR 인식 완료"
                            },
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth().align(Alignment.TopCenter).background(Color(0xAA000000)).padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedButton(onClick = onBack) { Text("닫기", color = Color.White) }
                Column(horizontalAlignment = Alignment.End) {
                    Text(if (setComponent == null) "QR 코드 스캔" else "${setComponent.label} 스캔", color = Color.White, fontWeight = FontWeight.Bold)
                    if (setComponent != null) Text(setProgress, color = HermesMint, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        Surface(
            color = Color.White,
            tonalElevation = 10.dp,
            shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
        ) {
            if (setComponent != null) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        SetComponent.entries.forEach { component ->
                            val shortLabel = if (component == SetComponent.TOP_COVER) "TOP" else component.label
                            if (component == setComponent) {
                                Button(
                                    onClick = { },
                                    contentPadding = ButtonDefaults.ContentPadding,
                                    colors = ButtonDefaults.buttonColors(containerColor = setComponentColor(component)),
                                    modifier = Modifier.weight(1f).height(42.dp),
                                ) { Text(shortLabel, style = MaterialTheme.typography.labelMedium) }
                            } else {
                                OutlinedButton(
                                    onClick = {
                                        resetScan()
                                        onSetComponentChange?.invoke(component)
                                    },
                                    contentPadding = ButtonDefaults.ContentPadding,
                                    modifier = Modifier.weight(1f).height(42.dp),
                                ) { Text(shortLabel, style = MaterialTheme.typography.labelMedium) }
                            }
                        }
                    }
                    Row(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("${setComponent.label} 선택", color = setComponentColor(setComponent), fontWeight = FontWeight.Bold)
                        Text(setProgress, fontWeight = FontWeight.Bold)
                    }
                    Row(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text("등급", color = HermesTextMuted, fontWeight = FontWeight.SemiBold)
                        listOf("A", "B", "F").forEach { grade ->
                            if (grade == setGrade) {
                                Button(
                                    onClick = { },
                                    contentPadding = ButtonDefaults.ContentPadding,
                                    modifier = Modifier.weight(1f).height(38.dp),
                                ) { Text("$grade 등급", style = MaterialTheme.typography.labelMedium) }
                            } else {
                                OutlinedButton(
                                    onClick = {
                                        resetScan()
                                        onSetGradeChange?.invoke(grade)
                                    },
                                    contentPadding = ButtonDefaults.ContentPadding,
                                    modifier = Modifier.weight(1f).height(38.dp),
                                ) { Text(grade, style = MaterialTheme.typography.labelMedium) }
                            }
                        }
                    }
                    if (parsed.itemCode.isNotBlank()) {
                        Row(Modifier.fillMaxWidth().padding(top = 5.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${parsed.itemCode} · ${setGrade.ifBlank { "등급 미선택" }}", fontWeight = FontWeight.Bold)
                            Text("LOT ${parsed.lot.ifBlank { "-" }}", fontWeight = FontWeight.Bold)
                        }
                    }
                    if (feedbackText.isNotBlank()) {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = if (feedbackSuccess == true) Color(0xFFE7F6F1) else Color(0xFFFFEAE4)),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
                        ) {
                            Text(feedbackText, color = if (feedbackSuccess == true) HermesGreen else HermesOrange, fontWeight = FontWeight.Bold, modifier = Modifier.padding(10.dp))
                        }
                    } else {
                        Text(if (validating) "품목과 LOT 재고를 확인하고 있습니다." else "QR을 화면 중앙에 맞추면 자동으로 확인됩니다.", color = HermesTextMuted, modifier = Modifier.padding(vertical = 6.dp))
                    }
                    if (feedbackSuccess != null) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth().padding(top = 6.dp)) {
                            OutlinedButton(
                                onClick = {
                                    if (feedbackSuccess == true) onUndoSetUse?.invoke()
                                    resetScan()
                                },
                                modifier = Modifier.weight(1f),
                            ) { Text(if (feedbackSuccess == true) "방금 배정 취소" else "다시 스캔") }
                            Button(onClick = { resetScan() }, modifier = Modifier.weight(1f)) {
                                Text(if (feedbackSuccess == true) "다음 스캔" else "다시 시도")
                            }
                        }
                    }
                }
            } else {
                Column(Modifier.fillMaxWidth().heightIn(max = 430.dp).verticalScroll(rememberScrollState()).padding(18.dp)) {
                    Text(if (parsed.itemCode.isBlank()) "QR 정보를 기다리는 중" else "QR 인식 완료", color = HermesGreen, fontWeight = FontWeight.Bold)
                    Text("품목코드: ${parsed.itemCode.ifBlank { "-" }}", fontWeight = FontWeight.Bold)
                    Text("명칭(QR): ${parsed.itemName.ifBlank { "-" }}")
                    Text("LOT: ${parsed.lot.ifBlank { "-" }} · 검사원: ${parsed.inspector.ifBlank { "-" }}")
                    Text("최초 입고일자: ${parsed.receivedDate.ifBlank { "-" }}")
                    Text(rawText, modifier = Modifier.padding(vertical = 8.dp))
                    Text("수량은 품목 확인 화면에서 입력합니다.", color = HermesTextMuted)
                    Spacer(Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        OutlinedButton(onClick = { resetScan() }, modifier = Modifier.weight(1f)) { Text("다시 스캔") }
                        Button(onClick = { onUse(parsed, 0) }, enabled = parsed.itemCode.isNotBlank(), modifier = Modifier.weight(1f)) { Text("품목 자동 조회") }
                    }
                }
            }
        }
    }
}

private fun parseMaterialQr(raw: String): QrMaterialData {
    val values = mutableMapOf<String, String>()
    raw.lineSequence().forEach { sourceLine ->
        val line = sourceLine.replace('：', ':').trim()
        val separator = line.indexOf(':')
        if (separator > 0) {
            val key = line.substring(0, separator).replace(" ", "").trim().uppercase()
            val value = line.substring(separator + 1).trim()
            values[key] = value
        }
    }
    fun value(vararg keys: String) = keys.firstNotNullOfOrNull { values[it]?.takeIf(String::isNotBlank) }.orEmpty()
    return QrMaterialData(
        itemName = value("명칭", "품목명"),
        itemCode = value("품목코드", "품목CODE", "ITEMCODE").uppercase(),
        receivedDate = value("입고일자", "최초입고일자"),
        lot = value("LOT", "Lot", "lot"),
        inspector = value("검사원"),
    )
}

@Composable
private fun MovementScreen(
    item: InventoryItem,
    initialQty: String,
    action: InventoryAction,
    qrData: QrMaterialData?,
    onBack: () -> Unit,
    onCompleted: (MovementResult, Int) -> Unit,
    onSessionExpired: () -> Unit,
) {
    var qtyText by rememberSaveable(item.id, action) {
        mutableStateOf(
            if (action == InventoryAction.LOT_REGISTER) initialQty.toIntOrNull()?.takeIf { it > 0 }?.toString().orEmpty()
            else initialQty.toIntOrNull()?.takeIf { it > 0 }?.toString() ?: "1"
        )
    }
    var remark by remember { mutableStateOf("") }
    var remarkOption by rememberSaveable(item.id, action) { mutableStateOf("") }
    var remarkExpanded by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var duplicateAt by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val actionLabel = when (action) {
        InventoryAction.IN -> "입고"
        InventoryAction.OUT -> "출고"
        InventoryAction.LOT_REGISTER -> "LOT 등록"
        InventoryAction.SET_OUT -> "세트 출고"
    }
    val actionAccent = when (action) {
        InventoryAction.IN -> HermesGreen
        InventoryAction.OUT -> HermesOrange
        InventoryAction.LOT_REGISTER -> HermesPurple
        InventoryAction.SET_OUT -> HermesGreen
    }
    val remarkOptions = when (action) {
        InventoryAction.OUT -> listOf("연구시료", "양산", "직접 입력")
        InventoryAction.IN -> listOf("연구시료 반납", "양산 반납", "직접 입력")
        else -> emptyList()
    }
    val finalRemark = when {
        remarkOptions.isEmpty() -> remark.trim()
        remarkOption == "직접 입력" -> remark.trim()
        else -> remarkOption
    }

    fun submit(skipDuplicateCheck: Boolean = false) {
        val qty = qtyText.toIntOrNull() ?: 0
        if (action != InventoryAction.LOT_REGISTER && qty <= 0) {
            message = "수량은 1 이상의 숫자로 입력하세요."
            return
        }
        if (qty < 0) {
            message = "수량은 0 이상의 숫자로 입력하세요."
            return
        }
        if (action == InventoryAction.LOT_REGISTER && qrData?.lot.isNullOrBlank()) {
            message = "LOT 등록은 LOT 정보가 포함된 QR 스캔이 필요합니다."
            return
        }
        if (action == InventoryAction.LOT_REGISTER && item.category != "원자재") {
            message = "LOT 등록은 원자재 품목만 가능합니다."
            return
        }
        loading = true
        scope.launch {
            if (!skipDuplicateCheck && qty > 0) {
                val duplicate = withContext(Dispatchers.IO) {
                    ApiClient.checkDuplicate(
                        itemId = item.id,
                        qty = qty,
                        inbound = action != InventoryAction.OUT,
                        lot = qrData?.lot.orEmpty(),
                    )
                }
                if (duplicate.error != null) {
                    loading = false
                    message = duplicate.error
                    if (duplicate.error.contains("로그인이 만료")) onSessionExpired()
                    return@launch
                }
                if (duplicate.value?.duplicate == true) {
                    loading = false
                    duplicateAt = duplicate.value.previousAt
                    return@launch
                }
            }
            val result = withContext(Dispatchers.IO) {
                if (action == InventoryAction.LOT_REGISTER) {
                    ApiClient.registerLot(
                        itemId = item.id,
                        qty = qty,
                        remark = finalRemark,
                        lot = qrData?.lot.orEmpty(),
                        inspector = qrData?.inspector.orEmpty(),
                        firstReceivedDate = qrData?.receivedDate.orEmpty(),
                        beforeQty = item.qty,
                        lotBeforeQty = item.lotQty,
                    )
                } else {
                    ApiClient.move(
                        itemId = item.id,
                        qty = qty,
                        remark = finalRemark,
                        inbound = action == InventoryAction.IN,
                        lot = qrData?.lot.orEmpty(),
                        inspector = qrData?.inspector.orEmpty(),
                        firstReceivedDate = qrData?.receivedDate.orEmpty(),
                        beforeQty = item.qty,
                        lotBeforeQty = item.lotQty,
                    )
                }
            }
            loading = false
            if (result.error != null) {
                message = result.error
                if (result.error.contains("로그인이 만료")) onSessionExpired()
            } else {
                onCompleted(result.value!!, qty)
            }
        }
    }

    if (duplicateAt != null) {
        AlertDialog(
            onDismissRequest = { duplicateAt = null },
            title = { Text("중복 처리 가능성이 있습니다") },
            text = {
                Text("같은 품목·LOT·작업·수량이 최근 3분 안에 처리되었습니다.\n최근 처리: ${duplicateAt.orEmpty()}\n\n실제로 연속 작업하는 경우에만 계속 진행하세요.")
            },
            dismissButton = {
                OutlinedButton(onClick = { duplicateAt = null }) { Text("취소") }
            },
            confirmButton = {
                Button(onClick = {
                    duplicateAt = null
                    submit(skipDuplicateCheck = true)
                }) { Text("그래도 처리") }
            },
        )
    }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(20.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedButton(onClick = onBack) { Text("← 이전") }
            Column(Modifier.padding(start = 12.dp)) {
                Text("FINAL CHECK", color = actionAccent, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelMedium)
                Text("$actionLabel 최종 확인", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            }
        }
        Spacer(Modifier.height(16.dp))
        Card(colors = CardDefaults.cardColors(containerColor = actionAccent.copy(alpha = 0.12f)), shape = RoundedCornerShape(16.dp)) {
            Text("$actionLabel · ${item.warehouseType}", color = actionAccent, fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth().padding(14.dp))
        }
        Spacer(Modifier.height(12.dp))
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(20.dp), elevation = CardDefaults.cardElevation(2.dp)) {
            Column(Modifier.fillMaxWidth().padding(18.dp)) {
                if (qrData != null) Text("✓ QR과 재고 품목 일치", color = HermesGreen, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodySmall)
                Text(item.itemCode, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 6.dp))
                Text(item.itemName, color = HermesTextMuted)
                Spacer(Modifier.height(12.dp))
                ProfileInfoRow("등급", item.grade.ifBlank { "-" })
                ProfileInfoRow("LOT", qrData?.lot.orEmpty().ifBlank { item.lot.ifBlank { "-" } })
                ProfileInfoRow("현재 재고", "${item.qty} EA")
            }
        }
        Spacer(Modifier.height(18.dp))
        OutlinedTextField(
            value = qtyText,
            onValueChange = { qtyText = it.filter(Char::isDigit) },
            label = { Text("수량") },
            supportingText = {
                if (action == InventoryAction.LOT_REGISTER) {
                    Text("선택사항 · 입력하면 LOT 잔량과 총재고가 함께 증가합니다.")
                }
            },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        val enteredQty = qtyText.toIntOrNull() ?: 0
        val afterTotal = when(action) {
            InventoryAction.OUT, InventoryAction.SET_OUT -> item.qty - enteredQty
            InventoryAction.IN, InventoryAction.LOT_REGISTER -> item.qty + enteredQty
        }
        val afterLot = when(action) {
            InventoryAction.OUT, InventoryAction.SET_OUT -> item.lotQty - enteredQty
            InventoryAction.IN, InventoryAction.LOT_REGISTER -> item.lotQty + enteredQty
        }
        Spacer(Modifier.height(12.dp))
        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFFE7F6F1)),
            shape = RoundedCornerShape(18.dp),
        ) {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text("처리 전후 예상 재고", color = actionAccent, fontWeight = FontWeight.Bold)
                ProfileInfoRow("전체 재고", "${item.qty} → $afterTotal EA")
                ProfileInfoRow("작업자", ApiClient.currentUser())
                if (!qrData?.lot.isNullOrBlank()) {
                    ProfileInfoRow("LOT 재고", "${item.lotQty} → $afterLot EA")
                }
                if (afterTotal < 0 || (!qrData?.lot.isNullOrBlank() && action == InventoryAction.OUT && afterLot < 0)) {
                    Text("재고가 부족하여 처리할 수 없습니다.", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.Bold)
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        if (remarkOptions.isNotEmpty()) {
            Text("비고", color = HermesTextMuted, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(6.dp))
            Box {
                Card(
                    modifier = Modifier.fillMaxWidth().clickable { remarkExpanded = true }.border(1.dp, HermesOutline, RoundedCornerShape(14.dp)),
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                ) {
                    Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text(remarkOption.ifBlank { "선택사항" }, color = if (remarkOption.isBlank()) HermesTextMuted else HermesNavy, fontWeight = if (remarkOption.isBlank()) FontWeight.Normal else FontWeight.Bold)
                        Icon(Icons.Filled.KeyboardArrowDown, contentDescription = "비고 선택")
                    }
                }
                DropdownMenu(expanded = remarkExpanded, onDismissRequest = { remarkExpanded = false }) {
                    remarkOptions.forEach { option ->
                        DropdownMenuItem(
                            text = { Text(option) },
                            onClick = {
                                remarkOption = option
                                remarkExpanded = false
                                if (option != "직접 입력") remark = ""
                            },
                        )
                    }
                }
            }
            if (remarkOption == "직접 입력") {
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = remark,
                    onValueChange = { remark = it },
                    label = { Text("비고 직접 입력") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        } else {
            OutlinedTextField(
                value = remark,
                onValueChange = { remark = it },
                label = { Text("비고") },
                modifier = Modifier.fillMaxWidth(),
            )
        }
        if (message.isNotBlank()) {
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEAE4)), shape = RoundedCornerShape(14.dp), modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp)) {
                Text(message, color = HermesOrange, fontWeight = FontWeight.Bold, modifier = Modifier.padding(12.dp))
            }
        }
        Button(
            onClick = { submit() },
            enabled = !loading && afterTotal >= 0 && (action != InventoryAction.OUT || qrData?.lot.isNullOrBlank() || afterLot >= 0),
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = actionAccent),
        ) {
            Text(
                when(action) {
                    InventoryAction.IN -> "입고 확정"
                    InventoryAction.OUT -> "출고 확정"
                    InventoryAction.LOT_REGISTER -> "LOT 등록 확정"
                    InventoryAction.SET_OUT -> "세트 출고 확정"
                }
            )
        }
    }
}
