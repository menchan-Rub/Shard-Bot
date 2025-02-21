const mongoose = require('mongoose');

const spamLogSchema = new mongoose.Schema({
  guildId: {
    type: String,
    required: true,
    index: true
  },
  userId: {
    type: String,
    required: true,
    ref: 'User',
    index: true
  },
  channelId: {
    type: String,
    required: true,
    index: true
  },
  messageContent: {
    type: String,
    maxLength: 2000
  },
  detectionType: {
    type: String,
    required: true,
    enum: [
      'messageSpam',      // メッセージスパム
      'mentionSpam',      // メンション荒らし
      'emojiSpam',        // 絵文字スパム
      'inviteSpam',       // 招待リンクスパム
      'linkSpam',         // 外部リンクスパム
      'duplicateSpam',    // 重複メッセージ
      'capsSpam',         // 大文字スパム
      'bannedWord',       // 禁止ワード
      'raidAttempt',      // レイド試行
      'suspiciousJoin',   // 不審な参加
      'other'             // その他
    ]
  },
  actionTaken: {
    type: String,
    required: true,
    enum: [
      'none',
      'delete',
      'warn',
      'mute',
      'kick',
      'ban'
    ]
  },
  details: {
    type: mongoose.Schema.Types.Mixed
  },
  createdAt: {
    type: Date,
    default: Date.now,
    expires: 7 * 24 * 60 * 60 // 7日後に自動削除
  }
}, {
  timestamps: true
});

// インデックスの設定
spamLogSchema.index({ guildId: 1, detectionType: 1 });
spamLogSchema.index({ guildId: 1, userId: 1 });
spamLogSchema.index({ createdAt: 1 });

// ログをフォーマット
spamLogSchema.methods.format = function() {
  return {
    id: this._id,
    guildId: this.guildId,
    userId: this.userId,
    channelId: this.channelId,
    messageContent: this.messageContent,
    detectionType: this.detectionType,
    actionTaken: this.actionTaken,
    details: this.details,
    createdAt: this.createdAt
  };
};

// 検出タイプごとの詳細フォーマット
spamLogSchema.methods.formatDetails = function() {
  const details = this.details || {};
  
  switch (this.detectionType) {
    case 'messageSpam':
      return {
        messageCount: details.messageCount,
        timeWindow: details.timeWindow,
        threshold: details.threshold
      };
      
    case 'mentionSpam':
      return {
        mentionCount: details.mentionCount,
        threshold: details.threshold,
        mentionedUsers: details.mentionedUsers
      };
      
    case 'emojiSpam':
      return {
        emojiCount: details.emojiCount,
        threshold: details.threshold,
        emojis: details.emojis
      };
      
    case 'inviteSpam':
    case 'linkSpam':
      return {
        linkCount: details.linkCount,
        links: details.links
      };
      
    case 'duplicateSpam':
      return {
        duplicateCount: details.duplicateCount,
        originalMessage: details.originalMessage
      };
      
    case 'capsSpam':
      return {
        capsPercentage: details.capsPercentage,
        threshold: details.threshold
      };
      
    case 'bannedWord':
      return {
        word: details.word,
        matchType: details.matchType
      };
      
    case 'raidAttempt':
    case 'suspiciousJoin':
      return {
        joinCount: details.joinCount,
        timeWindow: details.timeWindow,
        accountAge: details.accountAge
      };
      
    default:
      return details;
  }
};

// 静的メソッド

// ギルドのスパムログを取得
spamLogSchema.statics.getGuildLogs = function(guildId, options = {}) {
  const query = { guildId };
  
  if (options.detectionType) {
    query.detectionType = options.detectionType;
  }
  if (options.userId) {
    query.userId = options.userId;
  }
  if (options.channelId) {
    query.channelId = options.channelId;
  }
  
  return this.find(query)
    .sort({ createdAt: -1 })
    .limit(options.limit || 100)
    .skip(options.skip || 0);
};

// 検出タイプごとの統計を取得
spamLogSchema.statics.getDetectionStats = function(guildId, days = 7) {
  const since = new Date();
  since.setDate(since.getDate() - days);
  
  return this.aggregate([
    {
      $match: {
        guildId,
        createdAt: { $gte: since }
      }
    },
    {
      $group: {
        _id: '$detectionType',
        count: { $sum: 1 }
      }
    }
  ]);
};

// ユーザーごとの統計を取得
spamLogSchema.statics.getUserStats = function(guildId, startDate) {
  return this.aggregate([
    {
      $match: {
        guildId,
        createdAt: { $gte: startDate }
      }
    },
    {
      $group: {
        _id: '$userId',
        totalViolations: { $sum: 1 },
        detectionTypes: { $addToSet: '$detectionType' },
        actionsTaken: { $addToSet: '$actionTaken' },
        lastViolation: { $max: '$createdAt' }
      }
    },
    {
      $sort: { totalViolations: -1 }
    }
  ]);
};

spamLogSchema.statics.getUserViolations = function(guildId, userId) {
  return this.find({
    guildId,
    userId
  })
  .sort({ createdAt: -1 });
};

const SpamLog = mongoose.model('SpamLog', spamLogSchema);

module.exports = SpamLog; 