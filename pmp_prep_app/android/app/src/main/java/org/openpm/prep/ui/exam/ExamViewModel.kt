package org.openpm.prep.ui.exam

import android.os.SystemClock
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.openpm.engine.ExamEngine
import org.openpm.engine.ExamState
import org.openpm.engine.Phase
import org.openpm.engine.Response
import org.openpm.engine.Results
import org.openpm.prep.AppContainer

/**
 * Drives one attempt. The clock uses SystemClock.elapsedRealtime (monotonic: changing the device
 * clock has no effect). State is persisted every few seconds and after every action, so an attempt
 * resumes after process death. The exam clock pauses while the app is closed.
 */
class ExamViewModel(private val c: AppContainer, private val attemptId: String) : ViewModel() {
    private val _state = MutableStateFlow<ExamState?>(null)
    val state: StateFlow<ExamState?> = _state
    val bank = c.content.questions
    private var ticker: Job? = null
    private var unsavedStudyMs = 0L
    private var lastSave = 0L
    private val writeLock = Mutex()

    init {
        viewModelScope.launch {
            _state.value = c.progress.loadState(attemptId)
            if (_state.value?.phase != Phase.SUBMITTED) startTicker()
        }
    }

    private fun startTicker() {
        ticker?.cancel()
        ticker = viewModelScope.launch {
            var last = SystemClock.elapsedRealtime()
            while (true) {
                delay(250)
                val now = SystemClock.elapsedRealtime()
                val s = _state.value ?: continue
                val next = ExamEngine.tick(s, now - last, System.currentTimeMillis())
                if (s.phase == Phase.IN_SECTION) unsavedStudyMs += now - last
                last = now
                _state.value = next
                if (next.phase == Phase.SUBMITTED) { c.appScope.launch { finish(next) }; break }
                if (now - lastSave > 5_000) { persist(next); lastSave = now }
            }
        }
    }

    private fun update(f: (ExamState) -> ExamState) {
        val s = _state.value ?: return
        val n = f(s)
        if (n !== s) { _state.value = n; viewModelScope.launch { persist(n) } }
    }

    /**
     * All writes go through one mutex so an older save can never overwrite a newer one, and a
     * submitted attempt is always saved together with its result (never without it).
     */
    private suspend fun persist(s: ExamState) = writeLock.withLock {
        val latest = _state.value
        // Never let a stale in-progress snapshot overwrite a submitted attempt.
        val toSave = if (latest != null && latest.phase == Phase.SUBMITTED && s.phase != Phase.SUBMITTED) latest else s
        c.progress.saveAttempt(toSave, if (toSave.phase == Phase.SUBMITTED) Results.compute(toSave, bank) else null)
        if (unsavedStudyMs >= 1000) { c.progress.addStudySeconds(unsavedStudyMs / 1000); unsavedStudyMs %= 1000 }
    }

    private suspend fun finish(s: ExamState) = persist(s)

    fun answer(qid: String, r: Response) = update { ExamEngine.answer(it, qid, r) }
    fun reveal(qid: String) = update { ExamEngine.reveal(it, qid) }
    fun toggleMark(qid: String) = update { ExamEngine.toggleMark(it, qid) }
    fun goTo(i: Int) = update { ExamEngine.goTo(it, i) }
    fun next() = update { ExamEngine.next(it) }
    fun prev() = update { ExamEngine.prev(it) }
    fun finishSection() = update { ExamEngine.finishSection(it) }
    fun endBreak() = update { ExamEngine.endBreak(it) }

    fun submit() {
        val s = _state.value ?: return
        val n = ExamEngine.submit(s, System.currentTimeMillis())
        ticker?.cancel()
        _state.value = n
        c.appScope.launch { finish(n) }
    }

    /** Save on leave so nothing is lost. */
    fun saveNow() { _state.value?.let { s -> c.appScope.launch { persist(s) } } }

    override fun onCleared() { saveNow(); super.onCleared() }
}
