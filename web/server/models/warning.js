const mongoose = require('mongoose');

const warningSchema = new mongoose.Schema({
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
  moderatorId: {
    type: String,
    required: true,
    ref: 'User'
  },
  reason: {
    type: String,
    required: true,
    maxLength: 1000
  },
  active: {
    type: Boolean,
    default: true
  },
  expiresAt: {
    type: Date,
    sparse: true
  },
  deletedAt: {
    type: Date,
    sparse: true
  },
  deletedBy: {
    type: String,
    ref: 'User',
    sparse: true
  },
  deleteReason: {
    type: String,
    maxLength: 1000
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

// インデックスの設定
warningSchema.index({ guildId: 1, userId: 1 });
warningSchema.index({ active: 1, expiresAt: 1 });
warningSchema.index({ createdAt: 1 });

// メソッド
warningSchema.methods.toJSON = function() {
  const obj = this.toObject();
  delete obj.__v;
  return obj;
};

warningSchema.methods.delete = async function(moderatorId, reason) {
  this.active = false;
  this.deletedAt = new Date();
  this.deletedBy = moderatorId;
  this.deleteReason = reason;
  await this.save();
};

warningSchema.methods.isExpired = function() {
  return this.expiresAt && this.expiresAt <= new Date();
};

// スタティックメソッド
warningSchema.statics.getUserWarnings = function(guildId, userId) {
  return this.find({
    guildId,
    userId,
    active: true
  }).sort({ createdAt: -1 });
};

warningSchema.statics.getActiveWarnings = function(guildId, userId) {
  return this.find({
    guildId,
    userId,
    active: true,
    $or: [
      { expiresAt: { $gt: new Date() } },
      { expiresAt: null }
    ]
  });
};

warningSchema.statics.getModeratorStats = function(guildId, days = 30) {
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
        _id: '$moderatorId',
        warnings: { $sum: 1 }
      }
    },
    {
      $sort: { warnings: -1 }
    }
  ]);
};

warningSchema.statics.deleteExpiredWarnings = async function() {
  const now = new Date();
  const result = await this.updateMany(
    {
      active: true,
      expiresAt: { $lte: now }
    },
    {
      $set: {
        active: false,
        deletedAt: now,
        deleteReason: '警告期限切れ'
      }
    }
  );
  return result.modifiedCount;
};

const Warning = mongoose.model('Warning', warningSchema);

module.exports = Warning; 