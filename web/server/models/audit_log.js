const mongoose = require('mongoose');

const auditLogSchema = new mongoose.Schema({
  guildId: {
    type: String,
    required: true,
    index: true
  },
  actionType: {
    type: String,
    required: true,
    enum: [
      'memberBan',
      'memberUnban',
      'memberKick',
      'memberWarn',
      'memberMute',
      'memberUnmute',
      'messagePurge',
      'messagePin',
      'messageUnpin',
      'channelCreate',
      'channelUpdate',
      'channelDelete',
      'roleCreate',
      'roleUpdate',
      'roleDelete',
      'roleAssign',
      'roleRemove',
      'settingUpdate',
      'automodAction',
      'spamDetection',
      'raidDetection'
    ]
  },
  userId: {
    type: String,
    required: true,
    ref: 'User'
  },
  targetId: {
    type: String,
    ref: 'User'
  },
  reason: {
    type: String,
    maxLength: 1000
  },
  details: {
    type: mongoose.Schema.Types.Mixed
  },
  createdAt: {
    type: Date,
    default: Date.now,
    expires: 30 * 24 * 60 * 60 // 30日後に自動削除
  }
});

// インデックスの設定
auditLogSchema.index({ guildId: 1, actionType: 1 });
auditLogSchema.index({ guildId: 1, userId: 1 });
auditLogSchema.index({ createdAt: 1 });

// メソッド
auditLogSchema.methods.toJSON = function() {
  const obj = this.toObject();
  delete obj.__v;
  return obj;
};

auditLogSchema.methods.formatDetails = function() {
  const details = this.details || {};
  switch (this.actionType) {
    case 'memberBan':
    case 'memberUnban':
    case 'memberKick':
    case 'memberWarn':
    case 'memberMute':
    case 'memberUnmute':
      return {
        user: details.user,
        duration: details.duration,
        previousWarnings: details.previousWarnings
      };
    case 'messagePurge':
      return {
        channel: details.channel,
        count: details.count,
        filter: details.filter
      };
    case 'channelCreate':
    case 'channelUpdate':
    case 'channelDelete':
      return {
        name: details.name,
        type: details.type,
        category: details.category,
        permissions: details.permissions
      };
    case 'roleCreate':
    case 'roleUpdate':
    case 'roleDelete':
      return {
        name: details.name,
        color: details.color,
        permissions: details.permissions,
        position: details.position
      };
    case 'settingUpdate':
      return {
        setting: details.setting,
        oldValue: details.oldValue,
        newValue: details.newValue
      };
    case 'automodAction':
    case 'spamDetection':
    case 'raidDetection':
      return {
        trigger: details.trigger,
        action: details.action,
        content: details.content
      };
    default:
      return details;
  }
};

// スタティックメソッド
auditLogSchema.statics.getGuildLogs = function(guildId, options = {}) {
  const query = { guildId };
  
  if (options.actionType) {
    query.actionType = options.actionType;
  }
  if (options.userId) {
    query.userId = options.userId;
  }
  if (options.targetId) {
    query.targetId = options.targetId;
  }
  
  return this.find(query)
    .sort({ createdAt: -1 })
    .limit(options.limit || 100)
    .skip(options.skip || 0);
};

auditLogSchema.statics.getActionStats = function(guildId, days = 30) {
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
        _id: '$actionType',
        count: { $sum: 1 }
      }
    }
  ]);
};

const AuditLog = mongoose.model('AuditLog', auditLogSchema);

module.exports = AuditLog; 