const { AuditLog } = require('../models/audit_log');
const { SpamLog } = require('../models/spam_log');

class LogsController {
  static async getLogs(req, res) {
    try {
      const { guildId } = req.params;
      const { type, page = 1, limit = 50 } = req.query;

      const query = { guildId };
      if (type) {
        query.actionType = type;
      }

      const skip = (page - 1) * limit;
      
      const [logs, total] = await Promise.all([
        AuditLog.find(query)
          .sort({ createdAt: -1 })
          .skip(skip)
          .limit(parseInt(limit))
          .populate('userId', 'username')
          .populate('targetId', 'username'),
        AuditLog.countDocuments(query)
      ]);

      res.json({
        logs,
        total,
        page: parseInt(page),
        totalPages: Math.ceil(total / limit)
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get logs' });
    }
  }

  static async getSpamLogs(req, res) {
    try {
      const { guildId } = req.params;
      const { page = 1, limit = 50 } = req.query;

      const skip = (page - 1) * limit;
      
      const [logs, total] = await Promise.all([
        SpamLog.find({ guildId })
          .sort({ createdAt: -1 })
          .skip(skip)
          .limit(parseInt(limit))
          .populate('userId', 'username'),
        SpamLog.countDocuments({ guildId })
      ]);

      res.json({
        logs,
        total,
        page: parseInt(page),
        totalPages: Math.ceil(total / limit)
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get spam logs' });
    }
  }

  static async clearLogs(req, res) {
    try {
      const { guildId } = req.params;
      const { type } = req.query;

      if (type === 'spam') {
        await SpamLog.deleteMany({ guildId });
      } else if (type === 'audit') {
        await AuditLog.deleteMany({ guildId });
      } else {
        await Promise.all([
          SpamLog.deleteMany({ guildId }),
          AuditLog.deleteMany({ guildId })
        ]);
      }

      res.json({ message: 'Logs cleared successfully' });
    } catch (error) {
      res.status(500).json({ error: 'Failed to clear logs' });
    }
  }

  static async exportLogs(req, res) {
    try {
      const { guildId } = req.params;
      const { type, startDate, endDate } = req.query;

      const query = { guildId };
      if (startDate) {
        query.createdAt = { $gte: new Date(startDate) };
      }
      if (endDate) {
        query.createdAt = { ...query.createdAt, $lte: new Date(endDate) };
      }

      let logs;
      if (type === 'spam') {
        logs = await SpamLog.find(query)
          .sort({ createdAt: -1 })
          .populate('userId', 'username');
      } else {
        logs = await AuditLog.find(query)
          .sort({ createdAt: -1 })
          .populate('userId', 'username')
          .populate('targetId', 'username');
      }

      res.json(logs);
    } catch (error) {
      res.status(500).json({ error: 'Failed to export logs' });
    }
  }
}

module.exports = LogsController; 