const mongoose = require('mongoose');

const roleSchema = new mongoose.Schema({
  guildId: {
    type: String,
    required: true,
    index: true
  },
  roleId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  name: {
    type: String,
    required: true
  },
  color: {
    type: String,
    default: '#000000'
  },
  hoist: {
    type: Boolean,
    default: false
  },
  position: {
    type: Number,
    required: true
  },
  permissions: {
    type: String,
    required: true
  },
  mentionable: {
    type: Boolean,
    default: false
  },
  managed: {
    type: Boolean,
    default: false
  },
  isAdmin: {
    type: Boolean,
    default: false
  },
  isModerator: {
    type: Boolean,
    default: false
  },
  isMuted: {
    type: Boolean,
    default: false
  },
  memberCount: {
    type: Number,
    default: 0
  },
  stats: {
    assignCount: {
      type: Number,
      default: 0
    },
    removeCount: {
      type: Number,
      default: 0
    },
    lastAssigned: {
      type: Date
    },
    lastRemoved: {
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
roleSchema.index({ guildId: 1, roleId: 1 });
roleSchema.index({ guildId: 1, position: 1 });
roleSchema.index({ guildId: 1, isAdmin: 1 });
roleSchema.index({ guildId: 1, isModerator: 1 });

// メソッド
roleSchema.methods.toJSON = function() {
  const obj = this.toObject();
  delete obj.__v;
  return obj;
};

roleSchema.methods.updateStats = async function(action) {
  if (action === 'assign') {
    this.stats.assignCount++;
    this.stats.lastAssigned = new Date();
  } else if (action === 'remove') {
    this.stats.removeCount++;
    this.stats.lastRemoved = new Date();
  }
  await this.save();
};

roleSchema.methods.updateMemberCount = async function(count) {
  this.memberCount = count;
  await this.save();
};

// スタティックメソッド
roleSchema.statics.findByRoleId = function(roleId) {
  return this.findOne({ roleId });
};

roleSchema.statics.getGuildRoles = function(guildId) {
  return this.find({ guildId }).sort({ position: -1 });
};

roleSchema.statics.getAdminRoles = function(guildId) {
  return this.find({ guildId, isAdmin: true });
};

roleSchema.statics.getModeratorRoles = function(guildId) {
  return this.find({ guildId, isModerator: true });
};

roleSchema.statics.syncFromDiscord = async function(guildId, roles) {
  const operations = roles.map(role => ({
    updateOne: {
      filter: { roleId: role.id },
      update: {
        $set: {
          guildId,
          name: role.name,
          color: role.color,
          hoist: role.hoist,
          position: role.position,
          permissions: role.permissions,
          mentionable: role.mentionable,
          managed: role.managed,
          memberCount: role.members?.size || 0,
          updatedAt: new Date()
        }
      },
      upsert: true
    }
  }));

  await this.bulkWrite(operations);
};

const Role = mongoose.model('Role', roleSchema);

module.exports = Role; 