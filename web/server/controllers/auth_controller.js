const jwt = require('jsonwebtoken');
const { User } = require('../models/user');
const { OAuth2Client } = require('discord-oauth2');

const client = new OAuth2Client({
  clientId: process.env.DISCORD_CLIENT_ID,
  clientSecret: process.env.DISCORD_CLIENT_SECRET,
  redirectUri: process.env.DISCORD_REDIRECT_URI,
});

class AuthController {
  static async getDiscordOAuthUrl(req, res) {
    try {
      const url = client.generateAuthUrl({
        scope: ['identify', 'guilds'],
      });
      res.json({ url });
    } catch (error) {
      res.status(500).json({ error: 'Failed to generate OAuth URL' });
    }
  }

  static async handleDiscordCallback(req, res) {
    try {
      const { code } = req.body;
      const tokenData = await client.tokenRequest({
        code,
        grantType: 'authorization_code',
      });

      const userData = await client.getUser(tokenData.access_token);
      
      let user = await User.findOne({ discordId: userData.id });
      if (!user) {
        user = await User.create({
          discordId: userData.id,
          username: userData.username,
          email: userData.email,
          avatar: userData.avatar,
        });
      } else {
        user.username = userData.username;
        user.email = userData.email;
        user.avatar = userData.avatar;
        await user.save();
      }

      const token = jwt.sign(
        { userId: user.id },
        process.env.JWT_SECRET,
        { expiresIn: '24h' }
      );

      res.json({
        token,
        user: {
          id: user.id,
          username: user.username,
          email: user.email,
          avatar: user.avatar,
        },
      });
    } catch (error) {
      res.status(500).json({ error: 'Authentication failed' });
    }
  }

  static async getCurrentUser(req, res) {
    try {
      const user = await User.findById(req.user.id);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      res.json({
        id: user.id,
        username: user.username,
        email: user.email,
        avatar: user.avatar,
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get user data' });
    }
  }

  static async logout(req, res) {
    try {
      // トークンをブラックリストに追加するなどの処理をここに追加可能
      res.json({ message: 'Logged out successfully' });
    } catch (error) {
      res.status(500).json({ error: 'Logout failed' });
    }
  }
}

module.exports = AuthController; 