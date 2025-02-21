const mongoose = require('mongoose');

const guildSchema = new mongoose.Schema({
  guildId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  name: {
    type: String,
    required: true
  },
  icon: {
    type: String
  },
  ownerId: {
    type: String,
    required: true
  },
  isPremium: {
    type: Boolean,
    default: false
  },
  premiumUntil: {
    type: Date
  },
  memberCount: {
    type: Number,
    default: 0
  },
  botCount: {
    type: Number,
    default: 0
  },
  channelCount: {
    type: Number,
    default: 0
  },
  roleCount: {
    type: Number,
    default: 0
  },
  region: {
    type: String
  },
  features: [{
    type: String
  }],
  stats: {
    messages: {
      type: Number,
      default: 0
    },
    commands: {
      type: Number,
      default: 0
    },
    moderationActions: {
      type: Number,
      default: 0
    },
    spamDetections: {
      type: Number,
      default: 0
    },
    raidAttempts: {
      type: Number,
      default: 0
    }
  },
  dailyStats: [{
    date: {
      type: Date,
      required: true
    },
    messages: {
      type: Number,
      default: 0
    },
    commands: {
      type: Number,
      default: 0
    },
    moderationActions: {
      type: Number,
      default: 0
    },
    newMembers: {
      type: Number,
      default: 0
    },
    leftMembers: {
      type: Number,
      default: 0
    }
  }],
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
guildSchema.index({ guildId: 1 });
guildSchema.index({ isPremium: 1 });
guildSchema.index({ 'dailyStats.date': 1 });

// メソッド
guildSchema.methods.toJSON = function() {
  const obj = this.toObject();
  delete obj.__v;
  return obj;
};

guildSchema.methods.updateStats = async function(stats) {
  Object.assign(this.stats, stats);
  await this.save();
};

guildSchema.methods.addDailyStats = async function(stats) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const existingStats = this.dailyStats.find(s => 
    s.date.getTime() === today.getTime()
  );
  
  if (existingStats) {
    Object.assign(existingStats, stats);
  } else {
    this.dailyStats.push({
      date: today,
      ...stats
    });
  }
  
  // 30日以上前の統計を削除
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  this.dailyStats = this.dailyStats.filter(s => 
    s.date >= thirtyDaysAgo
  );
  
  await this.save();
};

// スタティックメソッド
guildSchema.statics.findByGuildId = function(guildId) {
  return this.findOne({ guildId });
};

guildSchema.statics.getPremiumGuilds = function() {
  return this.find({ isPremium: true });
};

guildSchema.statics.getTopGuilds = function(limit = 10) {
  return this.find()
    .sort({ memberCount: -1 })
    .limit(limit);
};

guildSchema.statics.updateGuildInfo = async function(guildId, info) {
  return this.findOneAndUpdate(
    { guildId },
    {
      $set: {
        name: info.name,
        icon: info.icon,
        ownerId: info.ownerId,
        memberCount: info.memberCount,
        botCount: info.botCount,
        channelCount: info.channelCount,
        roleCount: info.roleCount,
        region: info.region,
        features: info.features
      }
    },
    { new: true, upsert: true }
  );
};

const Guild = mongoose.model('Guild', guildSchema);

module.exports = Guild; 