const mongoose = require('mongoose');

const channelSchema = new mongoose.Schema({
  guildId: {
    type: String,
    required: true,
    index: true
  },
  channelId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  name: {
    type: String,
    required: true
  },
  type: {
    type: String,
    required: true,
    enum: ['text', 'voice', 'category', 'news', 'store', 'forum']
  },
  position: {
    type: Number,
    required: true
  },
  parentId: {
    type: String,
    sparse: true,
    ref: 'Channel'
  },
  topic: {
    type: String,
    maxLength: 1024
  },
  nsfw: {
    type: Boolean,
    default: false
  },
  rateLimitPerUser: {
    type: Number,
    default: 0
  },
  bitrate: {
    type: Number,
    sparse: true
  },
  userLimit: {
    type: Number,
    sparse: true
  },
  permissions: [{
    roleId: {
      type: String,
      required: true
    },
    allow: {
      type: String,
      required: true
    },
    deny: {
      type: String,
      required: true
    }
  }],
  isModLog: {
    type: Boolean,
    default: false
  },
  isWelcome: {
    type: Boolean,
    default: false
  },
  isAnnouncement: {
    type: Boolean,
    default: false
  },
  stats: {
    messageCount: {
      type: Number,
      default: 0
    },
    userCount: {
      type: Number,
      default: 0
    },
    lastMessage: {
      type: Date
    },
    lastActive: {
      type: Date
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
channelSchema.index({ guildId: 1, channelId: 1 });
channelSchema.index({ guildId: 1, type: 1 });
channelSchema.index({ guildId: 1, position: 1 });
channelSchema.index({ parentId: 1 });

// メソッド
channelSchema.methods.toJSON = function() {
  const obj = this.toObject();
  delete obj.__v;
  return obj;
};

channelSchema.methods.updateStats = async function(stats) {
  Object.assign(this.stats, stats);
  this.stats.lastActive = new Date();
  await this.save();
};

channelSchema.methods.incrementMessageCount = async function() {
  this.stats.messageCount++;
  this.stats.lastMessage = new Date();
  this.stats.lastActive = new Date();
  await this.save();
};

channelSchema.methods.updateUserCount = async function(count) {
  this.stats.userCount = count;
  this.stats.lastActive = new Date();
  await this.save();
};

// スタティックメソッド
channelSchema.statics.findByChannelId = function(channelId) {
  return this.findOne({ channelId });
};

channelSchema.statics.getGuildChannels = function(guildId) {
  return this.find({ guildId }).sort({ position: 1 });
};

channelSchema.statics.getCategories = function(guildId) {
  return this.find({
    guildId,
    type: 'category'
  }).sort({ position: 1 });
};

channelSchema.statics.getTextChannels = function(guildId) {
  return this.find({
    guildId,
    type: 'text'
  }).sort({ position: 1 });
};

channelSchema.statics.getVoiceChannels = function(guildId) {
  return this.find({
    guildId,
    type: 'voice'
  }).sort({ position: 1 });
};

channelSchema.statics.syncFromDiscord = async function(guildId, channels) {
  const operations = channels.map(channel => ({
    updateOne: {
      filter: { channelId: channel.id },
      update: {
        $set: {
          guildId,
          name: channel.name,
          type: channel.type,
          position: channel.position,
          parentId: channel.parentId,
          topic: channel.topic,
          nsfw: channel.nsfw,
          rateLimitPerUser: channel.rateLimitPerUser,
          bitrate: channel.bitrate,
          userLimit: channel.userLimit,
          permissions: channel.permissionOverwrites.cache.map(perm => ({
            roleId: perm.id,
            allow: perm.allow.toString(),
            deny: perm.deny.toString()
          })),
          updatedAt: new Date()
        }
      },
      upsert: true
    }
  }));

  await this.bulkWrite(operations);
};

const Channel = mongoose.model('Channel', channelSchema);

module.exports = Channel; 