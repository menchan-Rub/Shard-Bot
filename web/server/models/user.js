const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  discordId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  username: {
    type: String,
    required: true
  },
  email: {
    type: String,
    sparse: true
  },
  avatar: {
    type: String
  },
  isAdmin: {
    type: Boolean,
    default: false
  },
  isBanned: {
    type: Boolean,
    default: false
  },
  banReason: {
    type: String
  },
  guilds: [{
    type: String,
    ref: 'Guild'
  }],
  lastLogin: {
    type: Date,
    default: Date.now
  },
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  },
  // サーバーごとの設定
  guildSettings: [{
    guildId: {
      type: String,
      required: true,
    },
    nickname: String,
    roles: [String],
    joinedAt: Date,
    isMuted: {
      type: Boolean,
      default: false,
    },
    muteEndAt: Date,
  }],
}, {
  timestamps: true
});

// インデックスの設定
userSchema.index({ discordId: 1 });
userSchema.index({ guilds: 1 });
userSchema.index({ username: 'text' });
userSchema.index({ email: 1 });
userSchema.index({ createdAt: -1 });
userSchema.index({ lastLogin: -1 });
userSchema.index({ 'guildSettings.guildId': 1 });

// ユーザー情報をフォーマット
userSchema.methods.format = function() {
  return {
    id: this.discordId,
    username: this.username,
    email: this.email,
    avatar: this.avatar,
    isAdmin: this.isAdmin,
    guilds: this.guilds,
    lastLogin: this.lastLogin,
    createdAt: this.createdAt,
    updatedAt: this.updatedAt
  };
};

// ユーザーのアバターURLを取得
userSchema.methods.getAvatarUrl = function() {
  if (!this.avatar) return null;
  return `https://cdn.discordapp.com/avatars/${this.discordId}/${this.avatar}.png`;
};

// ユーザーをBANする
userSchema.methods.ban = async function(reason) {
  this.isBanned = true;
  this.banReason = reason;
  await this.save();
};

// ユーザーのBANを解除する
userSchema.methods.unban = async function() {
  this.isBanned = false;
  this.banReason = null;
  await this.save();
};

// ギルドを追加
userSchema.methods.addGuild = async function(guildId) {
  if (!this.guilds.includes(guildId)) {
    this.guilds.push(guildId);
    await this.save();
  }
};

// ギルドを削除
userSchema.methods.removeGuild = async function(guildId) {
  this.guilds = this.guilds.filter(id => id !== guildId);
  await this.save();
};

// ログイン時の更新
userSchema.methods.updateLoginTime = async function() {
  this.lastLogin = new Date();
  await this.save();
};

// メソッド
userSchema.methods.addWarning = function(guildId) {
  this.warnings += 1;
  this.warningDates.push(new Date());
  
  const guildSetting = this.guildSettings.find(s => s.guildId === guildId);
  if (guildSetting) {
    guildSetting.warnings = (guildSetting.warnings || 0) + 1;
  }
  
  return this.save();
};

userSchema.methods.clearWarnings = function(guildId) {
  this.warnings = 0;
  this.warningDates = [];
  
  const guildSetting = this.guildSettings.find(s => s.guildId === guildId);
  if (guildSetting) {
    guildSetting.warnings = 0;
  }
  
  return this.save();
};

userSchema.methods.mute = function(guildId, duration) {
  const guildSetting = this.guildSettings.find(s => s.guildId === guildId);
  if (guildSetting) {
    guildSetting.isMuted = true;
    guildSetting.muteEndAt = new Date(Date.now() + duration);
  }
  
  return this.save();
};

userSchema.methods.unmute = function(guildId) {
  const guildSetting = this.guildSettings.find(s => s.guildId === guildId);
  if (guildSetting) {
    guildSetting.isMuted = false;
    guildSetting.muteEndAt = null;
  }
  
  return this.save();
};

// メソッド
userSchema.methods.toJSON = function() {
  const obj = this.toObject();
  delete obj.__v;
  delete obj.banReason;
  return obj;
};

// 静的メソッド

// Discordユーザー情報から作成または更新
userSchema.statics.createOrUpdateFromDiscord = async function(userData) {
  const user = await this.findOne({ discordId: userData.id });
  if (user) {
    user.username = userData.username;
    user.email = userData.email;
    user.avatar = userData.avatar;
    await user.save();
    return user;
  }

  return await this.create({
    discordId: userData.id,
    username: userData.username,
    email: userData.email,
    avatar: userData.avatar
  });
};

// ユーザーを検索
userSchema.statics.findByDiscordId = function(discordId) {
  return this.findOne({ discordId });
};

// BANされたユーザーを取得
userSchema.statics.getBannedUsers = function() {
  return this.find({ isBanned: true });
};

// 管理者ユーザーを取得
userSchema.statics.getAdmins = function() {
  return this.find({ isAdmin: true });
};

userSchema.statics.findByGuildId = function(guildId, options = {}) {
  const query = { 'guildSettings.guildId': guildId };
  
  if (options.role) {
    query['guildSettings.roles'] = options.role;
  }
  
  if (options.muted !== undefined) {
    query['guildSettings.isMuted'] = options.muted;
  }
  
  if (options.banned !== undefined) {
    query['guildSettings.isBanned'] = options.banned;
  }
  
  return this.find(query);
};

const User = mongoose.model('User', userSchema);

module.exports = User; 