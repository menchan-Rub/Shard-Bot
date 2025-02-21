const mongoose = require('mongoose');

const settingsSchema = new mongoose.Schema({
  guildId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  // 基本設定
  prefix: {
    type: String,
    default: '!',
    maxLength: 10
  },
  language: {
    type: String,
    enum: ['ja', 'en', 'ko', 'zh'],
    default: 'ja'
  },
  timezone: {
    type: String,
    default: 'Asia/Tokyo'
  },
  // ロール設定
  modRoleId: {
    type: String,
    sparse: true
  },
  adminRoleId: {
    type: String,
    sparse: true
  },
  muteRoleId: {
    type: String,
    sparse: true
  },
  autoRoles: [{
    type: String,
    sparse: true
  }],
  // チャンネル設定
  logChannelId: {
    type: String,
    sparse: true
  },
  welcomeChannelId: {
    type: String,
    sparse: true
  },
  modLogChannelId: {
    type: String,
    sparse: true
  },
  // メッセージ設定
  welcomeMessage: {
    type: String,
    maxLength: 2000
  },
  leaveMessage: {
    type: String,
    maxLength: 2000
  },
  // 保護設定
  spamProtection: {
    enabled: {
      type: Boolean,
      default: true
    },
    messageLimit: {
      type: Number,
      default: 5
    },
    timeWindow: {
      type: Number,
      default: 5
    },
    mentionLimit: {
      type: Number,
      default: 5
    },
    emojiLimit: {
      type: Number,
      default: 20
    },
    punishment: {
      type: String,
      enum: ['warn', 'mute', 'kick', 'ban'],
      default: 'warn'
    }
  },
  raidProtection: {
    enabled: {
      type: Boolean,
      default: true
    },
    joinLimit: {
      type: Number,
      default: 10
    },
    timeWindow: {
      type: Number,
      default: 60
    },
    accountAge: {
      type: Number,
      default: 7
    },
    punishment: {
      type: String,
      enum: ['kick', 'ban'],
      default: 'kick'
    }
  },
  // 自動モデレーション設定
  automod: {
    enabled: {
      type: Boolean,
      default: true
    },
    bannedWords: [{
      type: String
    }],
    inviteLinks: {
      type: Boolean,
      default: true
    },
    duplicateMessages: {
      type: Boolean,
      default: true
    },
    capsLimit: {
      type: Number,
      default: 70
    },
    punishment: {
      type: String,
      enum: ['warn', 'mute', 'kick', 'ban'],
      default: 'warn'
    }
  },
  // 警告設定
  warnings: {
    maxWarnings: {
      type: Number,
      default: 3
    },
    punishment: {
      type: String,
      enum: ['mute', 'kick', 'ban'],
      default: 'mute'
    },
    expireAfter: {
      type: Number,
      default: 30
    }
  },
  // ミュート設定
  mute: {
    defaultDuration: {
      type: Number,
      default: 3600
    },
    maxDuration: {
      type: Number,
      default: 604800
    }
  },
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true
});

// インデックスの設定
settingsSchema.index({ guildId: 1 });

// 設定をフォーマット
settingsSchema.methods.format = function() {
  return {
    guildId: this.guildId,
    prefix: this.prefix,
    language: this.language,
    timezone: this.timezone,
    modRoleId: this.modRoleId,
    adminRoleId: this.adminRoleId,
    muteRoleId: this.muteRoleId,
    autoRoles: this.autoRoles,
    logChannelId: this.logChannelId,
    welcomeChannelId: this.welcomeChannelId,
    modLogChannelId: this.modLogChannelId,
    welcomeMessage: this.welcomeMessage,
    leaveMessage: this.leaveMessage,
    spamProtection: this.spamProtection,
    raidProtection: this.raidProtection,
    automod: this.automod,
    warnings: this.warnings,
    mute: this.mute,
    createdAt: this.createdAt,
    updatedAt: this.updatedAt
  };
};

// スパム保護が有効かどうか
settingsSchema.methods.isSpamProtected = function() {
  return this.spamProtection.enabled;
};

// レイド保護が有効かどうか
settingsSchema.methods.isRaidProtected = function() {
  return this.raidProtection.enabled;
};

// 自動モデレーションが有効かどうか
settingsSchema.methods.isAutoModEnabled = function() {
  return this.automod.enabled;
};

// 警告システムが有効かどうか
settingsSchema.methods.shouldWarn = function() {
  return this.warnings.maxWarnings > 0;
};

// デフォルト設定を取得
settingsSchema.statics.getDefaults = function() {
  return {
    prefix: '!',
    language: 'ja',
    timezone: 'Asia/Tokyo',
    spamProtection: {
      enabled: true,
      messageLimit: 5,
      timeWindow: 5,
      mentionLimit: 5,
      emojiLimit: 20,
      punishment: 'warn'
    },
    raidProtection: {
      enabled: true,
      joinLimit: 10,
      timeWindow: 60,
      accountAge: 7,
      punishment: 'kick'
    },
    automod: {
      enabled: true,
      bannedWords: [],
      inviteLinks: true,
      duplicateMessages: true,
      capsLimit: 70,
      punishment: 'warn'
    },
    warnings: {
      maxWarnings: 3,
      punishment: 'mute',
      expireAfter: 30
    },
    mute: {
      defaultDuration: 3600,
      maxDuration: 604800
    }
  };
};

// ギルドIDで設定を検索
settingsSchema.statics.findByGuildId = function(guildId) {
  return this.findOne({ guildId });
};

const Settings = mongoose.model('Settings', settingsSchema);

module.exports = Settings; 