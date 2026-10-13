package com.logisticssystem.app

import android.Manifest
import android.media.AudioManager
import android.media.ToneGenerator
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
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

private val HermesGreen = Color(0xFF006C5B)
private val HermesMint = Color(0xFF35D0A1)
private val HermesNavy = Color(0xFF102A2E)
private val HermesBackground = Color(0xFFF4F8F7)

private enum class SessionState { CHECKING, LOGGED_OUT, LOGGED_IN }
private enum class InventoryAction { IN, OUT, LOT_REGISTER }
private enum class MainTab { HOME, WORK, HISTORY, PROFILE }

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

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ApiClient.initialize(applicationContext)
        setContent {
            MaterialTheme {
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
    var action by rememberSaveable { mutableStateOf(InventoryAction.IN) }
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

    fun openScanner() {
        if (cameraGranted) showScanner = true
        else permissionLauncher.launch(Manifest.permission.CAMERA)
    }

    fun resetWork(nextAction: InventoryAction = action, completionMessage: String = "") {
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
                    showLotDetail = true
                }
            }
        }
    }

    if (showScanner) {
        LiveScannerScreen(
            quantityOptional = action == InventoryAction.LOT_REGISTER,
            onBack = { showScanner = false },
            onUse = { parsed, detectedQty ->
                qrData = parsed
                keyword = parsed.itemCode
                scanQty = if (detectedQty > 0) detectedQty.toString() else ""
                mainTab = MainTab.WORK
                results = emptyList()
                message = "QR 정보를 확인했습니다. 품목을 자동으로 조회합니다."
                showScanner = false
                search(parsed.itemCode)
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

    if (selected != null) {
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
            action = action,
            qrData = qrData,
            onBack = { selected = null },
            onCompleted = { result, quantity ->
                completion = CompletionData(action, selected!!, quantity, result, qrData)
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
                    selected = mainTab == MainTab.HISTORY,
                    onClick = {
                        mainTab = MainTab.HISTORY
                        loadHistory()
                    },
                    icon = { Icon(Icons.Filled.History, contentDescription = null) },
                    label = { Text("이력") },
                )
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
                onAction = {
                    selectAction(it)
                    mainTab = MainTab.WORK
                },
                onScan = { openScanner() },
            )
            MainTab.PROFILE -> ProfileScreen(
                modifier = Modifier.padding(scaffoldPadding),
                onLogout = onLogout,
            )
            MainTab.HISTORY -> HistoryScreen(
                modifier = Modifier.padding(scaffoldPadding),
                items = history,
                loading = historyLoading,
                message = historyMessage,
                onRefresh = { loadHistory() },
            )
            MainTab.WORK -> Column(
                Modifier
                    .fillMaxSize()
                    .padding(scaffoldPadding)
                    .verticalScroll(rememberScrollState())
                    .imePadding()
                    .padding(16.dp)
            ) {
        Text("재고 처리", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("QR 또는 품목 검색으로 입·출고를 처리하세요.", color = Color(0xFF61716F))
        Spacer(Modifier.height(18.dp))
        Card(
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
        ) {
            Column(Modifier.padding(18.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(28.dp).clip(RoundedCornerShape(9.dp)).background(HermesGreen), contentAlignment = Alignment.Center) {
                        Text("1", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                    Text("작업 유형 선택", fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 10.dp))
                }
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    ActionButton("입고", action == InventoryAction.IN, Modifier.weight(1f)) {
                        selectAction(InventoryAction.IN)
                    }
                    ActionButton("출고", action == InventoryAction.OUT, Modifier.weight(1f)) {
                        selectAction(InventoryAction.OUT)
                    }
                    ActionButton("LOT 등록", action == InventoryAction.LOT_REGISTER, Modifier.weight(1f)) {
                        selectAction(InventoryAction.LOT_REGISTER)
                    }
                }
                Text(
                    when(action) {
                        InventoryAction.IN -> "선택한 수량만큼 재고가 증가합니다."
                        InventoryAction.OUT -> "QR의 LOT 재고와 총재고가 함께 감소합니다."
                        InventoryAction.LOT_REGISTER -> "수량 입력 시 LOT와 총재고에 입고 반영합니다."
                    },
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        }
        Spacer(Modifier.height(16.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(28.dp).clip(RoundedCornerShape(9.dp)).background(HermesGreen), contentAlignment = Alignment.Center) {
                Text("2", color = Color.White, fontWeight = FontWeight.Bold)
            }
            Text("품목 및 수량", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 10.dp))
        }
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(
            value = keyword,
            onValueChange = {
                keyword = it
                qrData = null
            },
            label = { Text("품목코드 · 품목명 · LOT") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = warehouse,
            onValueChange = { warehouse = it },
            label = { Text("창고 유형") },
            supportingText = { Text("창고재고 / 제공재고 / 외주재고") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = scanQty,
            onValueChange = { scanQty = it.filter(Char::isDigit) },
            label = { Text("처리 수량") },
            supportingText = { Text(if (action == InventoryAction.OUT) "출고할 개수" else "입고할 개수") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        if (qrData != null) {
            Spacer(Modifier.height(10.dp))
            Card(
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFE7F6F1)),
            ) {
                Column(Modifier.fillMaxWidth().padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = HermesGreen)
                        Text("QR 정보 확인됨", color = HermesGreen, fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 8.dp))
                    }
                    Spacer(Modifier.height(10.dp))
                    Text("품목코드  ${qrData?.itemCode.orEmpty().ifBlank { "-" }}", fontWeight = FontWeight.Bold)
                    Text("LOT  ${qrData?.lot.orEmpty().ifBlank { "-" }}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text("입고일자  ${qrData?.receivedDate.orEmpty().ifBlank { "-" }}")
                    Text("검사원  ${qrData?.inspector.orEmpty().ifBlank { "-" }}")
                    if (action == InventoryAction.OUT) {
                        Text("등록되지 않았거나 잔량이 부족한 LOT는 출고가 차단됩니다.", color = Color(0xFF8A5A00), modifier = Modifier.padding(top = 8.dp))
                    }
                }
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(
                onClick = { openScanner() },
                modifier = Modifier.weight(1f),
            ) { Text("QR 스캔") }
            Button(onClick = { search() }, enabled = !loading, modifier = Modifier.weight(1f)) { Text("검색") }
        }
        if (loading) CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally).padding(12.dp))
        if (message.isNotBlank()) Text(message, modifier = Modifier.padding(vertical = 8.dp))
        if (results.isNotEmpty()) {
            Spacer(Modifier.height(8.dp))
            Text(
                "검색 결과 ${results.size}건",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(8.dp))
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                results.forEach { item ->
                Card(
                    modifier = Modifier.fillMaxWidth().clickable { selected = item },
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                ) {
                    Column(Modifier.padding(horizontal = 18.dp, vertical = 16.dp)) {
                        Text(
                            item.itemCode,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = HermesGreen,
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(item.itemName, style = MaterialTheme.typography.titleMedium)
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "${item.warehouseType} · 등급 ${item.grade.ifBlank { "-" }}",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Text(
                            "현재 재고 ${item.qty} EA",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                        )
                        Text("LOT ${item.lot.ifBlank { "-" }}", style = MaterialTheme.typography.bodySmall)
                    }
                }
                }
            }
        }
            }
        }
    }
}

@Composable
private fun HistoryScreen(
    modifier: Modifier = Modifier,
    items: List<InventoryHistoryItem>,
    loading: Boolean,
    message: String,
    onRefresh: () -> Unit,
) {
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 18.dp, vertical = 16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("처리 이력", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                Text("내 계정으로 처리한 최근 50건", color = Color(0xFF61716F))
            }
            OutlinedButton(onClick = onRefresh, enabled = !loading) { Text("새로고침") }
        }
        Spacer(Modifier.height(16.dp))
        Card(
            shape = RoundedCornerShape(18.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF6DF)),
        ) {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text("오처리 방지 안내", fontWeight = FontWeight.Bold, color = Color(0xFF8A5A00))
                Text(
                    "잘못 처리한 기록은 삭제하지 마세요. 원본 이력을 보존하고 관리자 확인 후 반대 거래로 정정해야 재고와 감사 기록이 함께 맞습니다.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
        if (loading) {
            CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally).padding(24.dp))
        } else if (message.isNotBlank()) {
            Text(message, modifier = Modifier.padding(vertical = 20.dp), color = Color(0xFF61716F))
        }
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items.forEach { item ->
                val inbound = item.movementType == "IN"
                val accent = if (inbound) HermesGreen else Color(0xFFB34B2D)
                val label = if (inbound) "입고" else "출고"
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
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
                            Text(item.createdAt, color = Color(0xFF61716F), modifier = Modifier.padding(start = 10.dp))
                            Spacer(Modifier.weight(1f))
                            Text("${item.qty} EA", color = accent, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        }
                        Spacer(Modifier.height(10.dp))
                        Text(item.itemCode, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                        Text(item.itemName)
                        Text("LOT ${item.lot.ifBlank { "-" }} · ${item.warehouseType}", color = Color(0xFF61716F))
                        if (item.inspector.isNotBlank()) Text("검사원 ${item.inspector}", color = Color(0xFF61716F))
                        if (item.source.isNotBlank()) Text("비고 ${item.source}", color = Color(0xFF61716F))
                    }
                }
            }
        }
        Spacer(Modifier.height(20.dp))
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
    }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(24.dp))
        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = HermesGreen, modifier = Modifier.size(76.dp))
        Spacer(Modifier.height(14.dp))
        Text("${label}이 완료되었습니다", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(data.item.itemCode, color = Color(0xFF61716F))
        Spacer(Modifier.height(22.dp))
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(22.dp)) {
            Column(Modifier.fillMaxWidth().padding(20.dp)) {
                Text("처리 결과", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                ProfileInfoRow("처리 수량", "${data.quantity} EA")
                ProfileInfoRow("전체 재고", "${data.result.beforeQty} → ${data.result.afterQty} EA")
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
    onAction: (InventoryAction) -> Unit,
    onScan: () -> Unit,
) {
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 18.dp)
    ) {
        Text("Logistics System", color = HermesGreen, fontWeight = FontWeight.Bold)
        if (BuildConfig.IS_DEV) {
            Text("DEV", color = Color.White, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 4.dp).clip(RoundedCornerShape(999.dp)).background(Color(0xFFE17A22)).padding(horizontal = 10.dp, vertical = 3.dp))
        }
        Text("오늘도 정확하게,", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("빠른 재고 처리를 시작하세요.", color = Color(0xFF61716F))
        Spacer(Modifier.height(22.dp))
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = HermesNavy),
        ) {
            Column(Modifier.padding(22.dp)) {
                Icon(Icons.Filled.QrCodeScanner, contentDescription = null, tint = HermesMint, modifier = Modifier.size(34.dp))
                Spacer(Modifier.height(14.dp))
                Text("QR로 바로 시작", color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text("품목코드와 LOT 정보를 한 번에 읽습니다.", color = Color(0xFFC8D7D5))
                Spacer(Modifier.height(18.dp))
                Button(onClick = onScan, modifier = Modifier.fillMaxWidth()) { Text("QR 스캔 열기") }
            }
        }
        Spacer(Modifier.height(24.dp))
        Text("빠른 작업", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(12.dp))
        ProductActionCard("입고", "재고 수량을 안전하게 증가", Color(0xFFE6F6F1), HermesGreen) { onAction(InventoryAction.IN) }
        Spacer(Modifier.height(10.dp))
        ProductActionCard("출고", "LOT 및 총재고 수량을 함께 차감", Color(0xFFFFF0EC), Color(0xFFB34B2D)) { onAction(InventoryAction.OUT) }
        Spacer(Modifier.height(10.dp))
        ProductActionCard("LOT 등록", "LOT 정보 등록 또는 수량 입고", Color(0xFFEEF0FF), Color(0xFF4C5DB6)) { onAction(InventoryAction.LOT_REGISTER) }
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
private fun ProfileScreen(modifier: Modifier = Modifier, onLogout: () -> Unit) {
    var devServerUrl by rememberSaveable { mutableStateOf(ApiClient.baseUrl()) }
    var serverMessage by remember { mutableStateOf("") }
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
        Text("내 정보", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("앱과 서버의 현재 상태를 확인하세요.", color = Color(0xFF61716F))
        Spacer(Modifier.height(18.dp))
        Card(shape = RoundedCornerShape(24.dp), colors = CardDefaults.cardColors(containerColor = HermesNavy)) {
            Column(Modifier.fillMaxWidth().padding(20.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(50.dp).clip(RoundedCornerShape(16.dp)).background(HermesGreen), contentAlignment = Alignment.Center) {
                        Icon(Icons.Filled.Person, contentDescription = null, tint = Color.White)
                    }
                    Column(Modifier.padding(start = 14.dp)) {
                        Text("현장 작업자", color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text("Logistics System", color = Color(0xFFC8D7D5))
                    }
                }
                Spacer(Modifier.height(18.dp))
                Row(Modifier.clip(RoundedCornerShape(12.dp)).background(Color(0xFF183E41)).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(9.dp).clip(RoundedCornerShape(99.dp)).background(HermesMint))
                    Text("서버 연결 준비됨", color = Color.White, modifier = Modifier.padding(start = 9.dp), fontWeight = FontWeight.Bold)
                }
            }
        }
        Spacer(Modifier.height(18.dp))
        Card(shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
            Column(Modifier.fillMaxWidth().padding(18.dp)) {
                Text("앱 정보", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(14.dp))
                ProfileInfoRow("앱 버전", BuildConfig.VERSION_NAME)
                ProfileInfoRow("환경", if (BuildConfig.IS_DEV) "DEV · local.db" else "PROD · Render/Neon")
                ProfileInfoRow("서버", ApiClient.baseUrl().removePrefix("https://").removePrefix("http://"))
                ProfileInfoRow("QR 인식", "ML Kit · 기기 내 처리")
            }
        }
        if (BuildConfig.IS_DEV) {
            Spacer(Modifier.height(14.dp))
            Card(shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF4E8))) {
                Column(Modifier.fillMaxWidth().padding(18.dp)) {
                    Text("DEV 서버 설정", color = Color(0xFF9A4D00), fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                    Text("노트북의 Wi-Fi IP와 8001 포트를 입력하세요.", color = Color(0xFF765B42), style = MaterialTheme.typography.bodySmall)
                    Spacer(Modifier.height(10.dp))
                    OutlinedTextField(
                        value = devServerUrl,
                        onValueChange = { devServerUrl = it },
                        label = { Text("개발 서버 주소") },
                        placeholder = { Text("http://200.200.40.38:8001") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    if (serverMessage.isNotBlank()) Text(serverMessage, color = Color(0xFF9A4D00), modifier = Modifier.padding(top = 6.dp))
                    Spacer(Modifier.height(10.dp))
                    Button(
                        onClick = {
                            val error = ApiClient.updateDevServerUrl(devServerUrl)
                            if (error == null) onLogout() else serverMessage = error
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("서버 주소 저장 후 다시 로그인") }
                }
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
    quantityOptional: Boolean,
    onBack: () -> Unit,
    onUse: (QrMaterialData, Int) -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var candidate by remember { mutableStateOf("") }
    var parsed by remember { mutableStateOf(QrMaterialData()) }
    var detectedQty by remember { mutableStateOf("") }
    var rawText by remember { mutableStateOf("QR 코드를 화면 중앙에 맞춰 주세요.") }
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
                            candidate = value
                            parsed = parseMaterialQr(value)
                            rawText = if (parsed.itemCode.isBlank()) {
                                "품목코드를 찾지 못했습니다. QR 형식을 확인해 주세요."
                            } else {
                                "QR 인식 완료 · 웹에서는 품목코드로 매칭합니다."
                            }
                            locked.set(parsed.itemCode.isNotBlank())
                            if (parsed.itemCode.isNotBlank()) {
                                toneGenerator.startTone(ToneGenerator.TONE_PROP_BEEP, 180)
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
                        brush = if (parsed.itemCode.isNotBlank()) {
                            Brush.linearGradient(listOf(Color(0xFF41F2B7), Color(0xFF00A77E), Color(0xFF9BFFD9)))
                        } else {
                            Brush.linearGradient(listOf(Color(0xCCFFFFFF), Color(0x66FFFFFF)))
                        },
                        shape = RoundedCornerShape(28.dp),
                    )
            ) {
                if (parsed.itemCode.isNotBlank()) {
                    Row(
                        modifier = Modifier.align(Alignment.TopCenter).padding(top = 14.dp).clip(RoundedCornerShape(999.dp)).background(Color(0xE6006C5B)).padding(horizontal = 14.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                        Text("인식 완료", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth().align(Alignment.TopCenter).background(Color(0xAA000000)).padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedButton(onClick = onBack) { Text("닫기", color = Color.White) }
                Text("QR 코드 스캔", color = Color.White, fontWeight = FontWeight.Bold)
            }
        }
        Surface(
            color = Color.White,
            tonalElevation = 10.dp,
            shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
        ) {
            Column(
                modifier = Modifier.fillMaxWidth().heightIn(max = 430.dp).verticalScroll(rememberScrollState()).padding(18.dp),
            ) {
            Text(if (parsed.itemCode.isBlank()) "QR 정보를 기다리는 중" else "QR 인식 완료", color = HermesGreen, fontWeight = FontWeight.Bold)
            Text("품목코드: ${parsed.itemCode.ifBlank { "-" }}", fontWeight = FontWeight.Bold)
            Text("명칭(QR): ${parsed.itemName.ifBlank { "-" }}")
            Text("LOT: ${parsed.lot.ifBlank { "-" }} · 검사원: ${parsed.inspector.ifBlank { "-" }}")
            Text("최초 입고일자: ${parsed.receivedDate.ifBlank { "-" }}")
            Text(rawText, modifier = Modifier.padding(vertical = 8.dp))
            OutlinedTextField(
                value = detectedQty,
                onValueChange = { detectedQty = it.filter(Char::isDigit) },
                label = { Text(if (quantityOptional) "입고 수량 (선택)" else "처리 수량 (필수)") },
                supportingText = {
                    Text(
                        if (quantityOptional) "선택사항 · 입력하면 LOT와 총재고에 입고 반영합니다."
                        else "수량은 직접 입력합니다."
                    )
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = {
                        candidate = ""
                        parsed = QrMaterialData()
                        detectedQty = ""
                        locked.set(false)
                        rawText = "QR 코드를 화면 중앙에 맞춰 주세요."
                    },
                    modifier = Modifier.weight(1f),
                ) { Text("다시 스캔") }
                Button(
                    onClick = { onUse(parsed, detectedQty.toIntOrNull() ?: 0) },
                    enabled = parsed.itemCode.isNotBlank() &&
                        (quantityOptional || (detectedQty.toIntOrNull() ?: 0) > 0),
                    modifier = Modifier.weight(1f),
                ) { Text("품목 자동 조회") }
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
    var message by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var duplicateAt by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

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
                        remark = remark.trim(),
                        lot = qrData?.lot.orEmpty(),
                        inspector = qrData?.inspector.orEmpty(),
                        firstReceivedDate = qrData?.receivedDate.orEmpty(),
                    )
                } else {
                    ApiClient.move(
                        itemId = item.id,
                        qty = qty,
                        remark = remark.trim(),
                        inbound = action == InventoryAction.IN,
                        lot = qrData?.lot.orEmpty(),
                        inspector = qrData?.inspector.orEmpty(),
                        firstReceivedDate = qrData?.receivedDate.orEmpty(),
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
        OutlinedButton(onClick = onBack) { Text("← 검색으로") }
        Spacer(Modifier.height(20.dp))
        Text(
            when(action) {
                InventoryAction.IN -> "입고 최종 확인"
                InventoryAction.OUT -> "출고 최종 확인"
                InventoryAction.LOT_REGISTER -> "LOT 등록 최종 확인"
            },
            color = HermesGreen,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(8.dp))
        Text(item.itemCode, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(item.itemName)
        Text("현재 전체 재고 ${item.qty} EA")
        if (qrData != null) {
            Spacer(Modifier.height(12.dp))
            Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
                Column(Modifier.padding(12.dp)) {
                    Text("QR 추적 정보", fontWeight = FontWeight.Bold)
                    Text("LOT: ${qrData.lot.ifBlank { "-" }}")
                    Text("검사원: ${qrData.inspector.ifBlank { "-" }}")
                    Text("최초 입고일자: ${qrData.receivedDate.ifBlank { "-" }}")
                    Text("품목명은 웹 등록명 '${item.itemName}'으로 기록됩니다.")
                }
            }
        }
        Spacer(Modifier.height(24.dp))
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
            InventoryAction.OUT -> item.qty - enteredQty
            InventoryAction.IN, InventoryAction.LOT_REGISTER -> item.qty + enteredQty
        }
        val afterLot = when(action) {
            InventoryAction.OUT -> item.lotQty - enteredQty
            InventoryAction.IN, InventoryAction.LOT_REGISTER -> item.lotQty + enteredQty
        }
        Spacer(Modifier.height(12.dp))
        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFFE7F6F1)),
            shape = RoundedCornerShape(18.dp),
        ) {
            Column(Modifier.fillMaxWidth().padding(16.dp)) {
                Text("처리 전후 예상 재고", color = HermesGreen, fontWeight = FontWeight.Bold)
                ProfileInfoRow("전체 재고", "${item.qty} → $afterTotal EA")
                if (!qrData?.lot.isNullOrBlank()) {
                    ProfileInfoRow("LOT 재고", "${item.lotQty} → $afterLot EA")
                }
                if (afterTotal < 0 || (!qrData?.lot.isNullOrBlank() && action == InventoryAction.OUT && afterLot < 0)) {
                    Text("재고가 부족하여 처리할 수 없습니다.", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.Bold)
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(
            value = remark,
            onValueChange = { remark = it },
            label = { Text("비고") },
            modifier = Modifier.fillMaxWidth(),
        )
        if (message.isNotBlank()) Text(message, modifier = Modifier.padding(vertical = 12.dp))
        Button(
            onClick = { submit() },
            enabled = !loading && afterTotal >= 0 && (action != InventoryAction.OUT || qrData?.lot.isNullOrBlank() || afterLot >= 0),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                when(action) {
                    InventoryAction.IN -> "입고 처리"
                    InventoryAction.OUT -> "출고 처리"
                    InventoryAction.LOT_REGISTER -> "LOT 등록"
                }
            )
        }
    }
}
