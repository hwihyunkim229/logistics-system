package com.logisticssystem.app

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONObject
import org.json.JSONArray
import java.io.BufferedReader
import java.net.CookieHandler
import java.net.CookieManager
import java.net.CookiePolicy
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class InventoryItem(
    val id: Int,
    val itemCode: String,
    val itemName: String,
    val category: String,
    val warehouseType: String,
    val lot: String,
    val grade: String,
    val rev: String,
    val qty: Int,
    val requestedLot: String,
    val lotQty: Int,
)

data class MovementResult(
    val beforeQty: Int,
    val afterQty: Int,
    val lot: String,
    val lotBeforeQty: Int,
    val lotAfterQty: Int,
)

data class DuplicateCheck(
    val duplicate: Boolean,
    val previousAt: String,
)

data class SetOutboundLine(
    val inventoryId: Int,
    val component: String,
    val lot: String,
    val qty: Int,
)

data class SetOutboundResult(
    val groupId: String,
    val setName: String,
    val targetSets: Int,
    val lineCount: Int,
    val totalQty: Int,
)

data class InventoryHistoryItem(
    val id: Int,
    val itemCode: String,
    val itemName: String,
    val warehouseType: String,
    val movementType: String,
    val qty: Int,
    val lot: String,
    val inspector: String,
    val source: String,
    val grade: String,
    val requestId: String,
    val setName: String,
    val setComponent: String,
    val setCount: Int,
    val createdAt: String,
)

data class ApiResult<T>(
    val value: T? = null,
    val error: String? = null,
    val requiresPasswordChange: Boolean = false,
)

object ApiClient {
    private const val PREFS_NAME = "logistics_session"
    private const val COOKIE_KEY = "session_cookie"
    private const val USER_KEY = "session_user"
    private const val DEV_SERVER_KEY = "dev_server_url"
    @Volatile private var sessionCookie: String? = null
    private var preferences: SharedPreferences? = null

    init {
        CookieHandler.setDefault(CookieManager(null, CookiePolicy.ACCEPT_ALL))
    }

    fun initialize(context: Context) {
        preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        sessionCookie = preferences?.getString(COOKIE_KEY, null)
    }

    fun hasStoredSession(): Boolean = !sessionCookie.isNullOrBlank()

    fun currentUser(): String = preferences?.getString(USER_KEY, "").orEmpty().ifBlank { "확인 중..." }

    fun baseUrl(): String {
        if (!BuildConfig.IS_DEV) return BuildConfig.API_BASE_URL
        return preferences?.getString(DEV_SERVER_KEY, BuildConfig.API_BASE_URL)
            ?.trim()
            ?.removeSuffix("/")
            .orEmpty()
            .ifBlank { BuildConfig.API_BASE_URL }
    }

    fun updateDevServerUrl(value: String): String? {
        if (!BuildConfig.IS_DEV) return "운영 앱에서는 서버 주소를 변경할 수 없습니다."
        val normalized = value.trim().removeSuffix("/login").removeSuffix("/")
        if (!normalized.startsWith("http://") && !normalized.startsWith("https://")) {
            return "http:// 또는 https://로 시작하는 주소를 입력하세요."
        }
        preferences?.edit()?.putString(DEV_SERVER_KEY, normalized)?.apply()
        sessionCookie = null
        preferences?.edit()?.remove(COOKIE_KEY)?.remove(USER_KEY)?.apply()
        (CookieHandler.getDefault() as? CookieManager)?.cookieStore?.removeAll()
        return null
    }

    fun login(username: String, password: String): ApiResult<Unit> {
        val body = "username=${encode(username)}&password=${encode(password)}"
        val response = request(
            path = "/login",
            method = "POST",
            body = body,
            contentType = "application/x-www-form-urlencoded",
        )
        if (response.code == 0) return ApiResult(error = response.message())
        if (response.code !in 200..299) return ApiResult(error = "아이디 또는 비밀번호를 확인하세요.")
        response.sessionCookie?.let {
            sessionCookie = it
            preferences?.edit()
                ?.putString(COOKIE_KEY, it)
                ?.putString(USER_KEY, username)
                ?.apply()
        }

        return runCatching {
            val json = JSONObject(response.body)
            if (!json.optBoolean("success")) ApiResult(error = "로그인에 실패했습니다.")
            else ApiResult(
                value = Unit,
                requiresPasswordChange = json.optBoolean("force_change"),
            )
        }.getOrElse {
            ApiResult(error = "서버 로그인 응답을 확인할 수 없습니다.")
        }
    }

    fun checkSession(): ApiResult<String> {
        if (sessionCookie.isNullOrBlank()) return ApiResult(error = "저장된 로그인이 없습니다.")
        val response = request("/inventory/mobile/session")
        if (response.code !in 200..299) return ApiResult(error = "로그인이 만료되었습니다.")
        return runCatching {
            val user = JSONObject(response.body).getString("user")
            preferences?.edit()?.putString(USER_KEY, user)?.apply()
            ApiResult(value = user)
        }.getOrElse { ApiResult(error = "로그인 상태를 확인할 수 없습니다.") }
    }

    fun logout() {
        runCatching { request("/logout") }
        sessionCookie = null
        preferences?.edit()?.remove(COOKIE_KEY)?.remove(USER_KEY)?.apply()
        (CookieHandler.getDefault() as? CookieManager)?.cookieStore?.removeAll()
    }

    fun searchItems(keyword: String, warehouseType: String, itemCode: String = "", lot: String = ""): ApiResult<List<InventoryItem>> {
        val path = buildString {
            append("/inventory/mobile/items?keyword=")
            append(encode(if (itemCode.isBlank()) keyword else ""))
            if (itemCode.isNotBlank()) {
                append("&item_code=")
                append(encode(itemCode))
            }
            if (lot.isNotBlank()) {
                append("&lot=")
                append(encode(lot))
            }
            if (warehouseType.isNotBlank()) {
                append("&warehouse_type=")
                append(encode(warehouseType))
            }
        }
        val response = request(path)
        if (response.code == 401 || response.code in 300..399) {
            return ApiResult(error = "로그인이 만료되었습니다. 다시 로그인하세요.")
        }
        if (response.code !in 200..299) return ApiResult(error = response.message())

        val array = JSONObject(response.body).getJSONArray("items")
        val items = buildList {
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                add(
                    InventoryItem(
                        id = item.getInt("id"),
                        itemCode = item.optString("item_code"),
                        itemName = item.optString("item_name"),
                        category = item.optString("category"),
                        warehouseType = item.optString("warehouse_type"),
                        lot = item.optString("lot"),
                        grade = item.optString("grade"),
                        rev = item.optString("rev"),
                        qty = item.optInt("qty"),
                        requestedLot = item.optString("requested_lot"),
                        lotQty = item.optInt("lot_qty"),
                    )
                )
            }
        }
        return ApiResult(value = items)
    }

    fun history(limit: Int = 50): ApiResult<List<InventoryHistoryItem>> {
        val response = request("/inventory/mobile/history?limit=$limit")
        if (response.code == 401 || response.code in 300..399) {
            return ApiResult(error = "로그인이 만료되었습니다. 다시 로그인하세요.")
        }
        if (response.code !in 200..299) return ApiResult(error = response.message())
        return runCatching {
            val array = JSONObject(response.body).getJSONArray("items")
            val items = buildList {
                for (index in 0 until array.length()) {
                    val item = array.getJSONObject(index)
                    add(
                        InventoryHistoryItem(
                            id = item.getInt("id"),
                            itemCode = item.optString("item_code"),
                            itemName = item.optString("item_name"),
                            warehouseType = item.optString("warehouse_type"),
                            movementType = item.optString("movement_type"),
                            qty = item.optInt("qty"),
                            lot = item.optString("lot"),
                            inspector = item.optString("inspector"),
                            source = item.optString("source"),
                            grade = item.optString("grade"),
                            requestId = item.optString("request_id"),
                            setName = item.optString("set_name"),
                            setComponent = item.optString("set_component"),
                            setCount = item.optInt("set_count"),
                            createdAt = item.optString("created_at"),
                        )
                    )
                }
            }
            ApiResult(value = items)
        }.getOrElse { ApiResult(error = "처리 이력을 읽을 수 없습니다.") }
    }

    fun checkDuplicate(
        itemId: Int,
        qty: Int,
        inbound: Boolean,
        lot: String,
    ): ApiResult<DuplicateCheck> {
        val json = JSONObject()
            .put("inventory_id", itemId)
            .put("qty", qty)
            .put("movement_type", if (inbound) "IN" else "OUT")
            .put("lot", lot)
        val response = request(
            path = "/inventory/mobile/duplicate-check",
            method = "POST",
            body = json.toString(),
            contentType = "application/json",
        )
        if (response.code == 401 || response.code in 300..399) {
            return ApiResult(error = "로그인이 만료되었습니다. 다시 로그인하세요.")
        }
        if (response.code == 404) return ApiResult(value = DuplicateCheck(false, ""))
        if (response.code !in 200..299) return ApiResult(error = response.message())
        return runCatching {
            val value = JSONObject(response.body)
            ApiResult(value = DuplicateCheck(value.optBoolean("duplicate"), value.optString("previous_at")))
        }.getOrElse { ApiResult(error = "중복 처리 여부를 확인할 수 없습니다.") }
    }

    fun move(
        itemId: Int,
        qty: Int,
        remark: String,
        inbound: Boolean,
        lot: String = "",
        inspector: String = "",
        firstReceivedDate: String = "",
        beforeQty: Int = 0,
        lotBeforeQty: Int = 0,
    ): ApiResult<MovementResult> {
        val json = JSONObject()
            .put("ids", JSONArray().put(itemId))
            .put("qty", qty)
            .put("remark", remark)
            .put("lot", lot)
            .put("inspector", inspector)
            .put("first_received_date", firstReceivedDate)
        val response = request(
            path = if (inbound) "/inventory/move-in" else "/inventory/move-out",
            method = "POST",
            body = json.toString(),
            contentType = "application/json",
        )
        if (response.code == 401 || response.code in 300..399) {
            return ApiResult(error = "로그인이 만료되었습니다. 다시 로그인하세요.")
        }
        if (response.code !in 200..299) return ApiResult(error = response.message())
        return parseMovementResult(
            response,
            MovementResult(
                beforeQty = beforeQty,
                afterQty = if (inbound) beforeQty + qty else beforeQty - qty,
                lot = lot,
                lotBeforeQty = lotBeforeQty,
                lotAfterQty = if (lot.isBlank()) 0 else if (inbound) lotBeforeQty + qty else lotBeforeQty - qty,
            ),
        )
    }

    fun setMoveOut(
        setName: String,
        targetSets: Int,
        requestId: String,
        lines: List<SetOutboundLine>,
        remark: String = "",
    ): ApiResult<SetOutboundResult> {
        val payloadLines = JSONArray()
        lines.forEach { line ->
            payloadLines.put(
                JSONObject()
                    .put("inventory_id", line.inventoryId)
                    .put("component", line.component)
                    .put("lot", line.lot)
                    .put("qty", line.qty)
            )
        }
        val body = JSONObject()
            .put("set_name", setName)
            .put("target_sets", targetSets)
            .put("request_id", requestId)
            .put("remark", remark)
            .put("lines", payloadLines)
        val response = request(
            path = "/inventory/mobile/set-move-out",
            method = "POST",
            body = body.toString(),
            contentType = "application/json",
        )
        if (response.code == 401 || response.code in 300..399) {
            return ApiResult(error = "로그인이 만료되었습니다. 다시 로그인하세요.")
        }
        if (response.code !in 200..299) return ApiResult(error = response.message())
        return runCatching {
            val json = JSONObject(response.body)
            val results = json.optJSONArray("results") ?: JSONArray()
            var totalQty = 0
            for (index in 0 until results.length()) {
                totalQty += results.getJSONObject(index).optInt("qty")
            }
            ApiResult(
                value = SetOutboundResult(
                    groupId = json.optString("group_id"),
                    setName = json.optString("set_name"),
                    targetSets = json.optInt("target_sets"),
                    lineCount = results.length(),
                    totalQty = totalQty,
                )
            )
        }.getOrElse { ApiResult(error = "세트 출고 결과를 확인할 수 없습니다.") }
    }

    fun registerLot(
        itemId: Int,
        qty: Int,
        remark: String,
        lot: String,
        inspector: String = "",
        firstReceivedDate: String = "",
        beforeQty: Int = 0,
        lotBeforeQty: Int = 0,
    ): ApiResult<MovementResult> {
        val json = JSONObject()
            .put("inventory_id", itemId)
            .put("qty", qty)
            .put("remark", remark)
            .put("lot", lot)
            .put("inspector", inspector)
            .put("first_received_date", firstReceivedDate)
        val response = request(
            path = "/inventory/lot-register",
            method = "POST",
            body = json.toString(),
            contentType = "application/json",
        )
        if (response.code == 401 || response.code in 300..399) {
            return ApiResult(error = "로그인이 만료되었습니다. 다시 로그인하세요.")
        }
        if (response.code !in 200..299) return ApiResult(error = response.message())
        return parseMovementResult(
            response,
            MovementResult(beforeQty, beforeQty + qty, lot, lotBeforeQty, lotBeforeQty + qty),
        )
    }

    private fun parseMovementResult(response: HttpResult, fallback: MovementResult): ApiResult<MovementResult> = runCatching {
        val row = JSONObject(response.body).getJSONArray("results").getJSONObject(0)
        ApiResult(
            value = MovementResult(
                beforeQty = row.optInt("before_qty"),
                afterQty = row.optInt("after_qty"),
                lot = row.optString("lot"),
                lotBeforeQty = row.optInt("lot_before_qty"),
                lotAfterQty = row.optInt("lot_after_qty"),
            )
        )
    }.getOrElse { ApiResult(value = fallback) }

    private fun request(
        path: String,
        method: String = "GET",
        body: String? = null,
        contentType: String = "application/json",
    ): HttpResult {
        val connection = (URL(baseUrl() + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 20_000
            readTimeout = 30_000
            instanceFollowRedirects = false
            setRequestProperty("Accept", "application/json")
            sessionCookie?.let { setRequestProperty("Cookie", it) }
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", contentType)
                outputStream.bufferedWriter(Charsets.UTF_8).use { it.write(body) }
            }
        }

        return try {
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use(BufferedReader::readText).orEmpty()
            val cookie = connection.headerFields.entries
                .firstOrNull { it.key?.equals("Set-Cookie", ignoreCase = true) == true }
                ?.value
                ?.firstOrNull()
                ?.substringBefore(';')
            HttpResult(code, text, cookie)
        } catch (error: Exception) {
            HttpResult(
                code = 0,
                body = JSONObject()
                    .put("message", "개발 서버에 연결할 수 없습니다. 서버 실행, Wi-Fi, 방화벽과 주소를 확인하세요. (${error.javaClass.simpleName})")
                    .toString(),
                sessionCookie = null,
            )
        } finally {
            connection.disconnect()
        }
    }

    private fun HttpResult.message(): String = runCatching {
        val json = JSONObject(body)
        json.optString("message").ifBlank {
            val detail = json.opt("detail")
            when (detail) {
                is String -> detail
                null -> "서버 요청에 실패했습니다. ($code)"
                else -> "요청 형식을 확인해 주세요. ($code): $detail"
            }
        }
    }.getOrDefault("서버 요청에 실패했습니다. ($code)")

    private fun encode(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())

    private data class HttpResult(
        val code: Int,
        val body: String,
        val sessionCookie: String? = null,
    )
}
