package org.openpm.prep.data

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

/** One practice test, demo or mock. [stateJson] holds the full serialized ExamState so attempts survive process death. */
@Entity(tableName = "attempts")
data class AttemptEntity(
    @PrimaryKey val id: String,
    val mode: String,
    val title: String,
    val startedAt: Long,
    val submittedAt: Long? = null,
    val scorePct: Double? = null,
    val questionCount: Int,
    val stateJson: String,
    val resultJson: String? = null,
    /** Sync flag for the optional cloud backend (Phase 8). */
    val dirty: Boolean = true,
)

@Entity(tableName = "lesson_progress")
data class LessonProgressEntity(
    @PrimaryKey val lessonId: String,
    val completedAt: Long? = null,
    val secondsSpent: Long = 0,
)

@Entity(tableName = "card_reviews")
data class CardReviewEntity(
    @PrimaryKey val cardId: String,
    val ease: Double,
    val intervalDays: Int,
    val repetitions: Int,
    val dueEpochDay: Long,
    val lastQuality: Int,
)

@Entity(tableName = "study_days")
data class StudyDayEntity(@PrimaryKey val epochDay: Long, val seconds: Long)

@Entity(tableName = "enquiries")
data class EnquiryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val institutionName: String,
    val contactName: String,
    val email: String,
    val message: String,
    val createdAt: Long,
    val submitted: Boolean = false,
)

@Entity(tableName = "feedback")
data class FeedbackEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val questionId: String?,
    val kind: String,
    val message: String,
    val createdAt: Long,
    val submitted: Boolean = false,
)

@Dao
interface PrepDao {
    @Upsert suspend fun upsertAttempt(a: AttemptEntity)
    @Query("SELECT * FROM attempts WHERE id = :id") suspend fun attempt(id: String): AttemptEntity?
    @Query("SELECT * FROM attempts WHERE id = :id") fun attemptFlow(id: String): Flow<AttemptEntity?>
    @Query("SELECT * FROM attempts ORDER BY startedAt DESC") fun attempts(): Flow<List<AttemptEntity>>
    @Query("DELETE FROM attempts WHERE id = :id") suspend fun deleteAttempt(id: String)
    @Query("SELECT stateJson FROM attempts ORDER BY startedAt DESC LIMIT :n") suspend fun recentStates(n: Int): List<String>

    @Query("SELECT * FROM lesson_progress") fun lessonProgress(): Flow<List<LessonProgressEntity>>
    @Query("SELECT * FROM lesson_progress WHERE lessonId = :id") suspend fun lesson(id: String): LessonProgressEntity?
    @Upsert suspend fun upsertLesson(p: LessonProgressEntity)

    @Query("SELECT * FROM card_reviews") fun cardReviews(): Flow<List<CardReviewEntity>>
    @Upsert suspend fun upsertCard(c: CardReviewEntity)

    @Query("SELECT * FROM study_days") fun studyDays(): Flow<List<StudyDayEntity>>
    @Query("SELECT * FROM study_days WHERE epochDay = :day") suspend fun studyDay(day: Long): StudyDayEntity?
    @Upsert suspend fun upsertStudyDay(d: StudyDayEntity)

    @Insert(onConflict = OnConflictStrategy.ABORT) suspend fun insertEnquiry(e: EnquiryEntity)
    @Query("SELECT * FROM enquiries ORDER BY createdAt DESC") fun enquiries(): Flow<List<EnquiryEntity>>
    @Insert suspend fun insertFeedback(f: FeedbackEntity)

    @Query("DELETE FROM attempts") suspend fun clearAttempts()
    @Query("DELETE FROM lesson_progress") suspend fun clearLessons()
    @Query("DELETE FROM card_reviews") suspend fun clearCards()
    @Query("DELETE FROM study_days") suspend fun clearDays()
    @Query("DELETE FROM enquiries") suspend fun clearEnquiries()
    @Query("DELETE FROM feedback") suspend fun clearFeedback()
}

@Database(
    entities = [AttemptEntity::class, LessonProgressEntity::class, CardReviewEntity::class, StudyDayEntity::class,
        EnquiryEntity::class, FeedbackEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class PrepDatabase : RoomDatabase() {
    abstract fun dao(): PrepDao

    companion object {
        fun build(context: Context): PrepDatabase =
            Room.databaseBuilder(context, PrepDatabase::class.java, "openpm-prep.db").build()
    }
}
