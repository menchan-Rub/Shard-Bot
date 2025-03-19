'use client'

import { useEffect, useState } from 'react'
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  Select,
  Spinner,
  useToast,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Center,
  useColorModeValue,
  Progress,
  Badge,
  Divider,
  FormControl,
  FormLabel,
  Input,
  InputGroup,
  InputRightElement,
  FormHelperText,
  Button,
  Switch,
  Textarea,
  Checkbox,
  Tooltip,
  Icon,
} from '@chakra-ui/react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import { 
  FaChartLine, 
  FaChartBar, 
  FaUsers, 
  FaComments, 
  FaTerminal, 
  FaBell, 
  FaList, 
  FaCog, 
  FaShieldAlt,
  FaServer,
  FaHashtag,
  FaTag,
  FaUser,
  FaQuestionCircle,
  FaUserPlus,
  FaToggleOn,
  FaHistory,
  FaSave,
} from 'react-icons/fa'

export default function Dashboard() {
  const [user, setUser] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [overview, setOverview] = useState<any>(null)
  const [analytics, setAnalytics] = useState([])
  const [guilds, setGuilds] = useState([])
  const [selectedGuild, setSelectedGuild] = useState<string | null>(null)
  const [guildStats, setGuildStats] = useState<any>(null)
  const [activeTab, setActiveTab] = useState(0)
  const [settings, setSettings] = useState<any>(null)
  const [channels, setChannels] = useState([])
  const [roles, setRoles] = useState([])
  const [isSaving, setIsSaving] = useState(false)
  const toast = useToast()

  // テーマ変数
  const cardBg = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.700')
  const textColor = useColorModeValue('gray.600', 'gray.400')
  const accentColor = useColorModeValue('purple.500', 'purple.300')

  // 初期データのロード
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) return

        // セッション情報を取得
        const sessionResponse = await fetch('/api/auth/session', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        })
        
        if (!sessionResponse.ok) {
          throw new Error('セッション情報の取得に失敗しました')
        }
        
        const sessionData = await sessionResponse.json()
        setUser(sessionData.data?.user)

        // サーバー一覧を取得
        const guildsResponse = await fetch('/api/guilds', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        })

        if (!guildsResponse.ok) {
          throw new Error('サーバー一覧の取得に失敗しました')
        }

        const guildsData = await guildsResponse.json()
        setGuilds(guildsData.guilds)
        
        // 最初のサーバーを選択
        if (guildsData.guilds.length > 0) {
          setSelectedGuild(guildsData.guilds[0].id)
        }

      } catch (error) {
        console.error('初期データの取得に失敗:', error)
        toast({
          title: 'エラー',
          description: error instanceof Error ? error.message : 'データの取得に失敗しました',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })
      }
    }

    fetchInitialData()
  }, [toast])

  // 全体の統計情報を取得
  useEffect(() => {
    const fetchOverviewData = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) return

        const [overviewData, analyticsData] = await Promise.all([
          fetch('/api/analytics/overview', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Accept': 'application/json',
            },
          }).then(res => res.json()),
          fetch('/api/analytics/', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Accept': 'application/json',
            },
          }).then(res => res.json()),
        ])

        setOverview(overviewData)
        setAnalytics(analyticsData)
      } catch (error) {
        console.error('統計データの取得に失敗:', error)
      }
    }

    fetchOverviewData()
  }, [])

  // 選択されたサーバーの統計情報を取得
  useEffect(() => {
    const fetchGuildStats = async () => {
      if (!selectedGuild) return

      try {
        const token = localStorage.getItem('token')
        if (!token) return

        const response = await fetch(`/api/analytics/guild/${selectedGuild}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error('サーバー統計の取得に失敗しました')
        }

        const data = await response.json()
        setGuildStats(data)
        setIsLoading(false)
      } catch (error) {
        console.error('サーバー統計の取得に失敗:', error)
        toast({
          title: 'エラー',
          description: error instanceof Error ? error.message : 'サーバー統計の取得に失敗しました',
          status: 'error',
          duration: 5000,
          isClosable: true,
        })
      }
    }

    fetchGuildStats()
  }, [selectedGuild, toast])

  // ボット設定のロード
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) return

        const response = await fetch('/api/settings', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error('ボット設定の取得に失敗しました')
        }

        const data = await response.json()
        setSettings(data)
      } catch (error) {
        console.error('ボット設定の取得に失敗:', error)
      }
    }

    fetchSettings()
  }, [])

  // チャンネルのロード
  useEffect(() => {
    const fetchChannels = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) return

        const response = await fetch('/api/channels', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error('チャンネルの取得に失敗しました')
        }

        const data = await response.json()
        setChannels(data)
      } catch (error) {
        console.error('チャンネルの取得に失敗:', error)
      }
    }

    fetchChannels()
  }, [])

  // ロールのロード
  useEffect(() => {
    const fetchRoles = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token || !selectedGuild) return

        const response = await fetch(`/api/roles?guildId=${selectedGuild}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error('ロールの取得に失敗しました')
        }

        const data = await response.json()
        setRoles(data)
      } catch (error) {
        console.error('ロールの取得に失敗:', error)
      }
    }

    if (selectedGuild) {
      fetchRoles()
    }
  }, [selectedGuild])

  // ボット設定を更新する関数
  const updateSetting = (key: string, value: any) => {
    setSettings((prev: any) => ({
      ...prev,
      [key]: value
    }))
  }

  // 設定を保存する関数
  const saveSettings = async (section: string) => {
    try {
      setIsSaving(true)
      const token = localStorage.getItem('token')
      if (!token) return

      const response = await fetch(`/api/settings/${section}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          guildId: selectedGuild,
          settings: settings
        }),
      })

      if (!response.ok) {
        throw new Error('設定の保存に失敗しました')
      }

      toast({
        title: '設定を保存しました',
        status: 'success',
        duration: 3000,
        isClosable: true,
      })
    } catch (error) {
      console.error('設定の保存に失敗:', error)
      toast({
        title: 'エラー',
        description: error instanceof Error ? error.message : '設定の保存に失敗しました',
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    )
  }

  // サーバー統計のUI
  return (
    <Container maxW="container.xl" py={8}>
      {isLoading ? (
        <Center h="50vh">
          <VStack spacing={4}>
            <Spinner size="xl" thickness="4px" color="purple.500" />
            <Text>データを読み込み中...</Text>
          </VStack>
        </Center>
      ) : (
        <>
          <Box mb={8}>
            <Heading as="h1" size="xl" mb={2} color={accentColor}>
              Shard Bot ダッシュボード
            </Heading>
            {user && (
              <HStack spacing={4} mb={6}>
                <Box 
                  p={3} 
                  borderRadius="md" 
                  bg={cardBg} 
                  boxShadow="md" 
                  borderWidth="1px"
                  borderColor={borderColor}
                >
                  <HStack spacing={3}>
                    <Icon as={FaUser} color="purple.500" />
                    <Text fontWeight="medium">{user.username}</Text>
                    <Badge colorScheme="purple">管理者</Badge>
                  </HStack>
                </Box>
                <Box 
                  p={3} 
                  borderRadius="md" 
                  bg={cardBg} 
                  boxShadow="md" 
                  borderWidth="1px"
                  borderColor={borderColor}
                >
                  <HStack spacing={3}>
                    <Icon as={FaServer} color="blue.500" />
                    <Text fontWeight="medium">管理中のサーバー数: {guilds.length}</Text>
                  </HStack>
                </Box>
              </HStack>
            )}
          </Box>

          <Tabs 
            variant="enclosed" 
            colorScheme="purple" 
            index={activeTab}
            onChange={setActiveTab}
            mb={6}
          >
            <TabList borderBottomWidth="2px" borderBottomColor={borderColor}>
              <Tab 
                _selected={{ color: accentColor, borderColor: accentColor, borderBottomWidth: "2px" }}
                fontWeight="medium"
              >
                <Icon as={FaChartBar} mr={2} />
                概要
              </Tab>
              <Tab 
                _selected={{ color: accentColor, borderColor: accentColor, borderBottomWidth: "2px" }}
                fontWeight="medium"
              >
                <Icon as={FaList} mr={2} />
                サーバー管理
              </Tab>
              <Tab 
                _selected={{ color: accentColor, borderColor: accentColor, borderBottomWidth: "2px" }}
                fontWeight="medium"
              >
                <Icon as={FaCog} mr={2} />
                設定
              </Tab>
              <Tab 
                _selected={{ color: accentColor, borderColor: accentColor, borderBottomWidth: "2px" }}
                fontWeight="medium"
              >
                <Icon as={FaShieldAlt} mr={2} />
                保護・監視
              </Tab>
            </TabList>

            <TabPanels mt={4}>
              {/* 概要タブ */}
              <TabPanel p={0}>
                <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
                  <StatCard 
                    title="総ユーザー数" 
                    value={overview?.totalUsers || 0} 
                    subtitle="全サーバー合計"
                    icon={FaUsers}
                    color="blue"
                  />
                  <StatCard 
                    title="処理メッセージ数" 
                    value={overview?.totalMessages || 0} 
                    subtitle="過去24時間"
                    icon={FaComments}
                    color="green"
                  />
                  <StatCard 
                    title="コマンド実行数" 
                    value={overview?.totalCommands || 0} 
                    subtitle="過去24時間"
                    icon={FaTerminal}
                    color="purple"
                  />
                  <StatCard 
                    title="イベント処理数" 
                    value={overview?.totalEvents || 0} 
                    subtitle="過去24時間"
                    icon={FaBell}
                    color="orange"
                  />
                </SimpleGrid>

                <Box 
                  mb={8} 
                  p={6} 
                  borderRadius="lg" 
                  boxShadow="md" 
                  bg={cardBg}
                  borderWidth="1px"
                  borderColor={borderColor}
                >
                  <Heading size="md" mb={4}>アクティビティグラフ</Heading>
                  <Box h="300px">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={analytics}>
                        <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                        <XAxis dataKey="time" stroke={textColor} />
                        <YAxis stroke={textColor} />
                        <RechartsTooltip contentStyle={{ backgroundColor: cardBg, borderColor: borderColor }} />
                        <Legend />
                        <Line type="monotone" dataKey="messages" stroke="#4299E1" strokeWidth={2} activeDot={{ r: 8 }} name="メッセージ" />
                        <Line type="monotone" dataKey="commands" stroke="#805AD5" strokeWidth={2} name="コマンド" />
                        <Line type="monotone" dataKey="events" stroke="#ED8936" strokeWidth={2} name="イベント" />
                      </LineChart>
                    </ResponsiveContainer>
                  </Box>
                </Box>

                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                  <Box 
                    p={6} 
                    borderRadius="lg" 
                    boxShadow="md" 
                    bg={cardBg}
                    borderWidth="1px"
                    borderColor={borderColor}
                  >
                    <Heading size="md" mb={4}>コマンド使用率</Heading>
                    <Box h="250px">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={overview?.commandUsage || []}>
                          <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                          <XAxis dataKey="name" stroke={textColor} />
                          <YAxis stroke={textColor} />
                          <RechartsTooltip contentStyle={{ backgroundColor: cardBg, borderColor: borderColor }} />
                          <Bar dataKey="count" fill="#805AD5" name="実行回数" />
                        </BarChart>
                      </ResponsiveContainer>
                    </Box>
                  </Box>

                  <Box 
                    p={6} 
                    borderRadius="lg" 
                    boxShadow="md" 
                    bg={cardBg}
                    borderWidth="1px"
                    borderColor={borderColor}
                  >
                    <Heading size="md" mb={4}>システム状態</Heading>
                    <VStack align="stretch" spacing={4}>
                      <HStack justify="space-between">
                        <Text>CPU使用率</Text>
                        <HStack>
                          <Progress 
                            value={overview?.system?.cpu || 0} 
                            size="sm" 
                            width="100px" 
                            colorScheme={overview?.system?.cpu > 80 ? "red" : "green"} 
                            borderRadius="full"
                          />
                          <Text fontWeight="medium">{overview?.system?.cpu || 0}%</Text>
                        </HStack>
                      </HStack>
                      
                      <HStack justify="space-between">
                        <Text>メモリ使用率</Text>
                        <HStack>
                          <Progress 
                            value={overview?.system?.memory || 0} 
                            size="sm" 
                            width="100px" 
                            colorScheme={overview?.system?.memory > 80 ? "red" : "blue"} 
                            borderRadius="full"
                          />
                          <Text fontWeight="medium">{overview?.system?.memory || 0}%</Text>
                        </HStack>
                      </HStack>
                      
                      <HStack justify="space-between">
                        <Text>レイテンシ</Text>
                        <Badge colorScheme={overview?.system?.latency < 100 ? "green" : "yellow"}>
                          {overview?.system?.latency || 0}ms
                        </Badge>
                      </HStack>
                      
                      <HStack justify="space-between">
                        <Text>稼働時間</Text>
                        <Text fontWeight="medium">{overview?.system?.uptime || "0日0時間"}</Text>
                      </HStack>
                    </VStack>
                  </Box>
                </SimpleGrid>
              </TabPanel>

              {/* サーバー管理タブ */}
              <TabPanel p={0}>
                <Box mb={6}>
                  <HStack mb={4}>
                    <Heading size="md">サーバー選択</Heading>
                    <Text color={textColor} fontSize="sm">管理するサーバーを選択してください</Text>
                  </HStack>
                  
          <Select
            placeholder="サーバーを選択"
            value={selectedGuild || ''}
            onChange={(e) => setSelectedGuild(e.target.value)}
                    bg={cardBg}
                    borderColor={borderColor}
          >
            {guilds.map((guild: any) => (
              <option key={guild.id} value={guild.id}>
                {guild.name}
              </option>
            ))}
          </Select>
        </Box>

                {selectedGuild && guildStats ? (
                <>
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6} mb={8}>
                    <StatCard
                        title="メンバー数"
                        value={guildStats.memberCount || 0} 
                        icon={FaUsers}
                        color="blue"
                    />
                    <StatCard
                        title="チャンネル数" 
                        value={guildStats.channelCount || 0} 
                        icon={FaHashtag}
                        color="green"
                    />
                    <StatCard
                        title="ロール数" 
                        value={guildStats.roleCount || 0} 
                        icon={FaTag}
                        color="purple"
                    />
                  </SimpleGrid>

                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                      <Box 
                        p={6} 
                        borderRadius="lg" 
                        boxShadow="md" 
                        bg={cardBg}
                        borderWidth="1px"
                        borderColor={borderColor}
                      >
                        <Heading size="md" mb={4}>サーバー情報</Heading>
                        <VStack align="stretch" spacing={3} divider={<Divider />}>
                          <HStack justify="space-between">
                            <Text fontWeight="medium">サーバー名</Text>
                            <Text>{guildStats.name}</Text>
                          </HStack>
                          <HStack justify="space-between">
                            <Text fontWeight="medium">作成日</Text>
                            <Text>{guildStats.createdAt}</Text>
                          </HStack>
                          <HStack justify="space-between">
                            <Text fontWeight="medium">オーナー</Text>
                            <Text>{guildStats.owner}</Text>
                          </HStack>
                          <HStack justify="space-between">
                            <Text fontWeight="medium">ブーストレベル</Text>
                            <Badge colorScheme="purple">レベル {guildStats.boostLevel || 0}</Badge>
                          </HStack>
                        </VStack>
                      </Box>

                      <Box 
                        p={6} 
                        borderRadius="lg" 
                        boxShadow="md" 
                        bg={cardBg}
                        borderWidth="1px"
                        borderColor={borderColor}
                      >
                        <Heading size="md" mb={4}>アクティビティ</Heading>
                        <VStack align="stretch" spacing={4}>
                          <VStack align="stretch" spacing={2}>
                            <Text fontSize="sm">過去24時間のメッセージ数</Text>
                            <Progress 
                              value={80} 
                              size="sm" 
                              colorScheme="blue" 
                              borderRadius="full"
                            />
                            <HStack justify="space-between">
                              <Text fontSize="xs" color={textColor}>0</Text>
                              <Text fontSize="sm" fontWeight="bold">{guildStats.messageCount || 0}</Text>
                              <Text fontSize="xs" color={textColor}>1000+</Text>
                            </HStack>
                          </VStack>
                          
                          <VStack align="stretch" spacing={2}>
                            <Text fontSize="sm">過去24時間のコマンド数</Text>
                            <Progress 
                              value={60} 
                              size="sm" 
                              colorScheme="purple" 
                              borderRadius="full"
                            />
                            <HStack justify="space-between">
                              <Text fontSize="xs" color={textColor}>0</Text>
                              <Text fontSize="sm" fontWeight="bold">{guildStats.commandCount || 0}</Text>
                              <Text fontSize="xs" color={textColor}>500+</Text>
                            </HStack>
                          </VStack>
                          
                          <VStack align="stretch" spacing={2}>
                            <Text fontSize="sm">過去24時間の参加メンバー数</Text>
                            <Progress 
                              value={30} 
                              size="sm" 
                              colorScheme="green" 
                              borderRadius="full"
                            />
                            <HStack justify="space-between">
                              <Text fontSize="xs" color={textColor}>0</Text>
                              <Text fontSize="sm" fontWeight="bold">{guildStats.joinCount || 0}</Text>
                              <Text fontSize="xs" color={textColor}>100+</Text>
                            </HStack>
                          </VStack>
                        </VStack>
                    </Box>
                    </SimpleGrid>
                  </>
                ) : selectedGuild ? (
                  <Center h="200px">
                    <Spinner />
                  </Center>
                ) : (
                  <Center 
                    h="200px" 
                    borderRadius="lg" 
                    borderWidth="1px" 
                    borderColor={borderColor} 
                    bg={cardBg} 
                    p={8}
                  >
                    <VStack>
                      <Icon as={FaServer} boxSize={10} color="gray.400" />
                      <Text color={textColor}>サーバーを選択してください</Text>
                    </VStack>
                  </Center>
              )}
            </TabPanel>

              {/* 設定タブ */}
              <TabPanel p={0}>
                <Box>
                  <Heading size="md" mb={6}>ボット設定</Heading>
                  
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={8}>
                    {/* 機能の有効/無効設定 */}
                    <Box 
                      p={6} 
                      borderRadius="lg" 
                      boxShadow="md" 
                      bg={cardBg}
                      borderWidth="1px"
                      borderColor={borderColor}
                    >
                      <Heading size="md" mb={4}>
                        <HStack>
                          <Icon as={FaToggleOn} color="purple.500" />
                          <Text>機能の有効/無効</Text>
                        </HStack>
                      </Heading>
                      
                      <VStack spacing={4} align="stretch">
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">レベルシステム</FormLabel>
                          <Switch 
                            isChecked={settings?.levelsEnabled} 
                            onChange={(e) => updateSetting('levelsEnabled', e.target.checked)}
                            colorScheme="purple"
                          />
                        </FormControl>
                        
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">自動モデレーション</FormLabel>
                          <Switch 
                            isChecked={settings?.automodEnabled} 
                            onChange={(e) => updateSetting('automodEnabled', e.target.checked)}
                            colorScheme="red"
                          />
                        </FormControl>
                        
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">レイド保護</FormLabel>
                          <Switch 
                            isChecked={settings?.raidProtectionEnabled} 
                            onChange={(e) => updateSetting('raidProtectionEnabled', e.target.checked)}
                            colorScheme="purple"
                          />
                        </FormControl>
                        
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">音楽機能</FormLabel>
                          <Switch 
                            isChecked={settings?.musicEnabled} 
                            onChange={(e) => updateSetting('musicEnabled', e.target.checked)}
                            colorScheme="teal"
                          />
                        </FormControl>
                        
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">自動応答機能</FormLabel>
                          <Switch 
                            isChecked={settings?.autoResponseEnabled} 
                            onChange={(e) => updateSetting('autoResponseEnabled', e.target.checked)}
                            colorScheme="blue"
                          />
                        </FormControl>
                      </VStack>
                      
                      <Button 
                        mt={6} 
                        colorScheme="purple" 
                        leftIcon={<FaSave />}
                        isLoading={isSaving}
                        onClick={() => saveSettings('features')}
                      >
                        保存
                      </Button>
                    </Box>
                    
                    {/* ログ設定 */}
                    <Box 
                      p={6} 
                      borderRadius="lg" 
                      boxShadow="md" 
                      bg={cardBg}
                      borderWidth="1px"
                      borderColor={borderColor}
                    >
                      <Heading size="md" mb={4}>
                        <HStack>
                          <Icon as={FaHistory} color="orange.500" />
                          <Text>ログ設定</Text>
                        </HStack>
                      </Heading>
                      
                      <VStack spacing={4} align="stretch">
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">ログ機能</FormLabel>
                          <Switch 
                            isChecked={settings?.loggingEnabled} 
                            onChange={(e) => updateSetting('loggingEnabled', e.target.checked)}
                            colorScheme="orange"
                          />
                        </FormControl>
                        
                        <FormControl isDisabled={!settings?.loggingEnabled}>
                          <FormLabel>ログチャンネル</FormLabel>
                          <Select 
                            placeholder="チャンネルを選択" 
                            value={settings?.logChannelId || ""} 
                            onChange={(e) => updateSetting('logChannelId', e.target.value)}
                          >
                            {channels.map((channel: any) => (
                              <option key={channel.id} value={channel.id}>
                                #{channel.name}
                              </option>
                            ))}
                          </Select>
                          <FormHelperText>ログの送信先チャンネル</FormHelperText>
                        </FormControl>
                        
                        <Text fontWeight="medium" mt={2}>ログに記録する項目:</Text>
                        
                        <SimpleGrid columns={2} spacing={2}>
                          <Checkbox 
                            isChecked={settings?.logMessageDelete}
                            onChange={(e) => updateSetting('logMessageDelete', e.target.checked)}
                          >
                            メッセージ削除
                          </Checkbox>
                          
                          <Checkbox 
                            isChecked={settings?.logMessageEdit}
                            onChange={(e) => updateSetting('logMessageEdit', e.target.checked)}
                          >
                            メッセージ編集
                          </Checkbox>
                          
                          <Checkbox 
                            isChecked={settings?.logMemberJoin}
                            onChange={(e) => updateSetting('logMemberJoin', e.target.checked)}
                          >
                            メンバー参加
                          </Checkbox>
                          
                          <Checkbox 
                            isChecked={settings?.logMemberLeave}
                            onChange={(e) => updateSetting('logMemberLeave', e.target.checked)}
                          >
                            メンバー退出
                          </Checkbox>
                          
                          <Checkbox 
                            isChecked={settings?.logMemberBan}
                            onChange={(e) => updateSetting('logMemberBan', e.target.checked)}
                          >
                            メンバーBAN
                          </Checkbox>
                          
                          <Checkbox 
                            isChecked={settings?.logChannelChanges}
                            onChange={(e) => updateSetting('logChannelChanges', e.target.checked)}
                          >
                            チャンネル変更
                          </Checkbox>
                          
                          <Checkbox 
                            isChecked={settings?.logRoleChanges}
                            onChange={(e) => updateSetting('logRoleChanges', e.target.checked)}
                          >
                            ロール変更
                          </Checkbox>
                          
                          <Checkbox 
                            isChecked={settings?.logVoiceChanges}
                            onChange={(e) => updateSetting('logVoiceChanges', e.target.checked)}
                          >
                            ボイスチャンネル
                          </Checkbox>
                    </SimpleGrid>
                      </VStack>
                      
                      <Button 
                        mt={6} 
                        colorScheme="orange" 
                        leftIcon={<FaSave />}
                        isLoading={isSaving}
                        onClick={() => saveSettings('logs')}
                      >
                        保存
                      </Button>
                        </Box>
                  </SimpleGrid>
                      </Box>
              </TabPanel>
              
              <TabPanel>
                <Box>
                  <Heading size="md" mb={6}>保護・監視設定</Heading>
                  
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={8}>
                    {/* 自動モデレーション設定 */}
                    <Box 
                      p={6} 
                      borderRadius="lg" 
                      boxShadow="md" 
                      bg={cardBg}
                      borderWidth="1px"
                      borderColor={borderColor}
                    >
                      <Heading size="md" mb={4}>
                        <HStack>
                          <Icon as={FaShieldAlt} color="red.500" />
                          <Text>自動モデレーション</Text>
                        </HStack>
                      </Heading>
                      
                      <VStack spacing={4} align="stretch">
                        {/* 自動モデレーションの有効/無効 */}
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">自動モデレーション機能</FormLabel>
                          <Switch 
                            isChecked={settings?.autoModEnabled} 
                            onChange={(e) => updateSetting('autoModEnabled', e.target.checked)}
                            colorScheme="red"
                          />
                        </FormControl>
                        
                        <Divider />
                        
                        <Text fontWeight="medium">フィルター設定:</Text>
                        
                        {/* 禁止ワードフィルター */}
                        <FormControl isDisabled={!settings?.autoModEnabled}>
                          <HStack justifyContent="space-between">
                            <FormLabel mb="0">禁止ワードフィルター</FormLabel>
                            <Switch 
                              isChecked={settings?.filterBadWords} 
                              onChange={(e) => updateSetting('filterBadWords', e.target.checked)}
                              colorScheme="red"
                              size="sm"
                            />
                          </HStack>
                          <FormHelperText>不適切な言葉を自動的に検出し、削除します</FormHelperText>
                        </FormControl>
                        
                        {/* カスタム禁止ワード */}
                        <FormControl isDisabled={!settings?.autoModEnabled || !settings?.filterBadWords}>
                          <FormLabel>カスタム禁止ワード</FormLabel>
                          <Textarea
                            placeholder="各禁止ワードは改行または、カンマで区切ってください"
                            value={settings?.customBadWords || ""}
                            onChange={(e) => updateSetting('customBadWords', e.target.value)}
                            rows={3}
                          />
                          <FormHelperText>
                            独自に設定する禁止ワードのリスト
                          </FormHelperText>
                        </FormControl>
                        
                        <Divider />
                        
                        {/* 招待リンクフィルター */}
                        <FormControl isDisabled={!settings?.autoModEnabled}>
                          <HStack justifyContent="space-between">
                            <FormLabel mb="0">招待リンクフィルター</FormLabel>
                            <Switch 
                              isChecked={settings?.filterInvites} 
                              onChange={(e) => updateSetting('filterInvites', e.target.checked)}
                              colorScheme="red"
                              size="sm"
                            />
                          </HStack>
                          <FormHelperText>他のDiscordサーバーへの招待リンクを自動的に削除します</FormHelperText>
                        </FormControl>
                        
                        {/* URLフィルター */}
                        <FormControl isDisabled={!settings?.autoModEnabled}>
                          <HStack justifyContent="space-between">
                            <FormLabel mb="0">URLフィルター</FormLabel>
                            <Switch 
                              isChecked={settings?.filterLinks} 
                              onChange={(e) => updateSetting('filterLinks', e.target.checked)}
                              colorScheme="red"
                              size="sm"
                            />
                          </HStack>
                          <FormHelperText>URLを含むメッセージを自動的に削除します</FormHelperText>
                        </FormControl>
                        
                        {/* 許可されたURL */}
                        <FormControl isDisabled={!settings?.autoModEnabled || !settings?.filterLinks}>
                          <FormLabel>許可するURL</FormLabel>
                          <Textarea
                            placeholder="例: youtube.com, twitter.com"
                            value={settings?.allowedLinks || ""}
                            onChange={(e) => updateSetting('allowedLinks', e.target.value)}
                            rows={2}
                          />
                          <FormHelperText>
                            フィルターの例外とするURLのリスト
                          </FormHelperText>
                        </FormControl>
                      </VStack>
                      
                      <Button 
                        mt={6} 
                        colorScheme="red" 
                        leftIcon={<FaSave />}
                        isLoading={isSaving}
                        onClick={() => saveSettings('automod')}
                      >
                        保存
                      </Button>
                        </Box>
                    
                    {/* アンチスパム設定 */}
                    <Box 
                      p={6} 
                      borderRadius="lg" 
                      boxShadow="md" 
                      bg={cardBg}
                      borderWidth="1px"
                      borderColor={borderColor}
                    >
                      <Heading size="md" mb={4}>
                        <HStack>
                          <Icon as={FaBell} color="orange.500" />
                          <Text>アンチスパム</Text>
                        </HStack>
                      </Heading>
                      
                      <VStack spacing={4} align="stretch">
                        {/* アンチスパムの有効/無効 */}
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">アンチスパム機能</FormLabel>
                          <Switch 
                            isChecked={settings?.antiSpamEnabled} 
                            onChange={(e) => updateSetting('antiSpamEnabled', e.target.checked)}
                            colorScheme="orange"
                          />
                        </FormControl>
                        
                        <Divider />
                        
                        {/* 同一メッセージの連続投稿制限 */}
                        <FormControl isDisabled={!settings?.antiSpamEnabled}>
                          <FormLabel>同一メッセージの連続投稿制限</FormLabel>
                          <HStack>
                            <Input 
                              type="number" 
                              value={settings?.duplicateMessageThreshold || 3}
                              onChange={(e) => updateSetting('duplicateMessageThreshold', parseInt(e.target.value))}
                              maxW="100px"
                            />
                            <Text>メッセージ / </Text>
                            <Input 
                              type="number" 
                              value={settings?.duplicateMessageTimeframe || 10}
                              onChange={(e) => updateSetting('duplicateMessageTimeframe', parseInt(e.target.value))}
                              maxW="100px"
                            />
                            <Text>秒</Text>
                          </HStack>
                          <FormHelperText>短時間に同じ内容のメッセージが連続で投稿された場合に検出します</FormHelperText>
                        </FormControl>
                        
                        {/* 連続メッセージ制限 */}
                        <FormControl isDisabled={!settings?.antiSpamEnabled}>
                          <FormLabel>連続メッセージ制限</FormLabel>
                          <HStack>
                            <Input 
                              type="number" 
                              value={settings?.messageSpamThreshold || 5}
                              onChange={(e) => updateSetting('messageSpamThreshold', parseInt(e.target.value))}
                              maxW="100px"
                            />
                            <Text>メッセージ / </Text>
                            <Input 
                              type="number" 
                              value={settings?.messageSpamTimeframe || 3}
                              onChange={(e) => updateSetting('messageSpamTimeframe', parseInt(e.target.value))}
                              maxW="100px"
                            />
                            <Text>秒</Text>
                          </HStack>
                          <FormHelperText>短時間に大量のメッセージが投稿された場合に検出します</FormHelperText>
                        </FormControl>
                        
                        <Divider />
                        
                        {/* メンション制限 */}
                        <FormControl isDisabled={!settings?.antiSpamEnabled}>
                          <FormLabel>メンション制限</FormLabel>
                          <HStack>
                            <Input 
                              type="number" 
                              value={settings?.mentionLimit || 5}
                              onChange={(e) => updateSetting('mentionLimit', parseInt(e.target.value))}
                              maxW="100px"
                            />
                            <Text>メンション / メッセージ</Text>
                          </HStack>
                          <FormHelperText>1つのメッセージに含まれるメンション数を制限します</FormHelperText>
                        </FormControl>
                        
                        <Divider />
                        
                        {/* 制裁アクション */}
                        <FormControl isDisabled={!settings?.antiSpamEnabled}>
                          <FormLabel>スパム検出時のアクション</FormLabel>
                          <Select 
                            value={settings?.spamAction || "delete"} 
                            onChange={(e) => updateSetting('spamAction', e.target.value)}
                          >
                            <option value="delete">メッセージを削除</option>
                            <option value="warn">警告を送信</option>
                            <option value="mute">一時的にミュート (タイムアウト)</option>
                            <option value="kick">サーバーからキック</option>
                            <option value="ban">サーバーからBAN</option>
                          </Select>
                          <FormHelperText>スパムが検出された場合の対応</FormHelperText>
                        </FormControl>
                      </VStack>
                      
                      <Button 
                        mt={6} 
                        colorScheme="orange" 
                        leftIcon={<FaSave />}
                        isLoading={isSaving}
                        onClick={() => saveSettings('antispam')}
                      >
                        保存
                      </Button>
                      </Box>
                    </SimpleGrid>
                  
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={8} mt={8}>
                    {/* レイド保護設定 */}
                    <Box 
                      p={6} 
                      borderRadius="lg" 
                      boxShadow="md" 
                      bg={cardBg}
                      borderWidth="1px"
                      borderColor={borderColor}
                    >
                      <Heading size="md" mb={4}>
                        <HStack>
                          <Icon as={FaUsers} color="purple.500" />
                          <Text>レイド保護</Text>
                        </HStack>
                      </Heading>
                      
                      <VStack spacing={4} align="stretch">
                        {/* レイド保護の有効/無効 */}
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">レイド保護機能</FormLabel>
                          <Switch 
                            isChecked={settings?.raidProtectionEnabled} 
                            onChange={(e) => updateSetting('raidProtectionEnabled', e.target.checked)}
                            colorScheme="purple"
                          />
                        </FormControl>
                        
                        <Divider />
                        
                        {/* レイド検出設定 */}
                        <FormControl isDisabled={!settings?.raidProtectionEnabled}>
                          <FormLabel>レイド検出設定</FormLabel>
                          <HStack>
                            <Input 
                              type="number" 
                              value={settings?.raidThreshold || 10}
                              onChange={(e) => updateSetting('raidThreshold', parseInt(e.target.value))}
                              maxW="100px"
                            />
                            <Text>アカウント / </Text>
                            <Input 
                              type="number" 
                              value={settings?.raidTimeframe || 60}
                              onChange={(e) => updateSetting('raidTimeframe', parseInt(e.target.value))}
                              maxW="100px"
                            />
                            <Text>秒</Text>
                          </HStack>
                          <FormHelperText>短時間に大量のアカウントが参加した場合にレイドとして検出します</FormHelperText>
                        </FormControl>
                        
                        <Divider />
                        
                        {/* レイド検出時のアクション */}
                        <FormControl isDisabled={!settings?.raidProtectionEnabled}>
                          <FormLabel>レイド検出時のアクション</FormLabel>
                          <Select 
                            value={settings?.raidAction || "lockdown"} 
                            onChange={(e) => updateSetting('raidAction', e.target.value)}
                          >
                            <option value="alert">モデレーターに通知</option>
                            <option value="lockdown">サーバーをロックダウン</option>
                            <option value="verification">認証レベルを上げる</option>
                            <option value="ban">新規参加者をBAN</option>
                          </Select>
                          <FormHelperText>レイドが検出された場合の対応</FormHelperText>
                        </FormControl>
                        
                        <Divider />
                        
                        {/* 新規アカウント制限 */}
                        <FormControl isDisabled={!settings?.raidProtectionEnabled}>
                          <FormLabel>新規アカウント制限</FormLabel>
                          <HStack>
                            <Input 
                              type="number" 
                              value={settings?.accountAgeLimit || 7}
                              onChange={(e) => updateSetting('accountAgeLimit', parseInt(e.target.value))}
                              maxW="100px"
                            />
                            <Text>日以内のアカウントを拒否</Text>
                          </HStack>
                          <FormHelperText>作成から一定日数以内のアカウントの参加を拒否します (0で無効)</FormHelperText>
                        </FormControl>
                        
                        {/* 認証要求 */}
                        <FormControl display="flex" alignItems="center" isDisabled={!settings?.raidProtectionEnabled}>
                          <FormLabel mb="0">参加時に認証を要求</FormLabel>
                          <Switch 
                            isChecked={settings?.requireVerification} 
                            onChange={(e) => updateSetting('requireVerification', e.target.checked)}
                            colorScheme="blue"
                          />
                        </FormControl>
                      </VStack>
                      
                      <Button 
                        mt={6} 
                        colorScheme="purple" 
                        leftIcon={<FaSave />}
                        isLoading={isSaving}
                        onClick={() => saveSettings('raidprotection')}
                      >
                        保存
                      </Button>
                    </Box>
                    
                    {/* キャプチャ設定 */}
                    <Box 
                      p={6} 
                      borderRadius="lg" 
                      boxShadow="md" 
                      bg={cardBg}
                      borderWidth="1px"
                      borderColor={borderColor}
                    >
                      <Heading size="md" mb={4}>
                        <HStack>
                          <Icon as={FaUser} color="teal.500" />
                          <Text>認証・キャプチャ</Text>
                        </HStack>
                      </Heading>
                      
                      <VStack spacing={4} align="stretch">
                        {/* キャプチャの有効/無効 */}
                        <FormControl display="flex" alignItems="center">
                          <FormLabel mb="0">キャプチャ認証</FormLabel>
                          <Switch 
                            isChecked={settings?.captchaEnabled} 
                            onChange={(e) => updateSetting('captchaEnabled', e.target.checked)}
                            colorScheme="teal"
                          />
                        </FormControl>
                        
                        <Divider />
                        
                        {/* キャプチャタイプ */}
                        <FormControl isDisabled={!settings?.captchaEnabled}>
                          <FormLabel>キャプチャタイプ</FormLabel>
                          <Select 
                            value={settings?.captchaType || "text"} 
                            onChange={(e) => updateSetting('captchaType', e.target.value)}
                          >
                            <option value="text">テキスト認証</option>
                            <option value="emoji">絵文字認証</option>
                            <option value="math">数学問題</option>
                            <option value="image">画像認証</option>
                          </Select>
                          <FormHelperText>使用するキャプチャのタイプ</FormHelperText>
                        </FormControl>
                        
                        {/* キャプチャチャンネル */}
                        <FormControl isDisabled={!settings?.captchaEnabled}>
                          <FormLabel>キャプチャチャンネル</FormLabel>
                          <Select 
                            placeholder="チャンネルを選択" 
                            value={settings?.captchaChannelId || ""} 
                            onChange={(e) => updateSetting('captchaChannelId', e.target.value)}
                          >
                            {channels.map((channel: any) => (
                              <option key={channel.id} value={channel.id}>
                                #{channel.name}
                              </option>
                            ))}
                          </Select>
                          <FormHelperText>キャプチャを表示するチャンネル</FormHelperText>
                        </FormControl>
                        
                        <Divider />
                        
                        {/* 認証成功時に付与するロール */}
                        <FormControl isDisabled={!settings?.captchaEnabled}>
                          <FormLabel>認証成功時のロール</FormLabel>
                          <Select 
                            placeholder="ロールを選択" 
                            value={settings?.verifiedRoleId || ""} 
                            onChange={(e) => updateSetting('verifiedRoleId', e.target.value)}
                          >
                            {roles.map((role: any) => (
                              <option key={role.id} value={role.id}>
                                {role.name}
                              </option>
                            ))}
                          </Select>
                          <FormHelperText>認証に成功したユーザーに付与するロール</FormHelperText>
                        </FormControl>
                        
                        {/* 認証メッセージ */}
                        <FormControl isDisabled={!settings?.captchaEnabled}>
                          <FormLabel>認証メッセージ</FormLabel>
                          <Textarea
                            placeholder="サーバーへようこそ！認証を完了するために、表示されたキャプチャコードを入力してください。"
                            value={settings?.captchaMessage || "サーバーへようこそ！認証を完了するために、表示されたキャプチャコードを入力してください。"}
                            onChange={(e) => updateSetting('captchaMessage', e.target.value)}
                            rows={3}
                          />
                          <FormHelperText>認証画面に表示するメッセージ</FormHelperText>
                        </FormControl>
                      </VStack>
                      
                      <Button 
                        mt={6} 
                        colorScheme="teal" 
                        leftIcon={<FaSave />}
                        isLoading={isSaving}
                        onClick={() => saveSettings('captcha')}
                      >
                        保存
                      </Button>
                    </Box>
                  </SimpleGrid>
                </Box>
              </TabPanel>
          </TabPanels>
        </Tabs>
        </>
      )}
    </Container>
  )
}

// StatCardコンポーネントを強化
interface StatCardProps {
  title: string;
  value: number;
  subtitle?: string;
  icon?: React.ElementType;
  color?: string;
}

const StatCard = ({ title, value, subtitle, icon, color = "blue" }: StatCardProps) => {
  const cardBg = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.700')
  const textColor = useColorModeValue('gray.600', 'gray.400')
  const IconComponent = icon || FaChartLine

  return (
    <Box
      p={6}
      borderRadius="lg"
      boxShadow="md"
      bg={cardBg}
      borderWidth="1px"
      borderColor={borderColor}
      position="relative"
      overflow="hidden"
    >
      <Box 
        position="absolute" 
        top={0} 
        right={0} 
        bg={`${color}.50`} 
        _dark={{ bg: `${color}.900`, opacity: 0.2 }}
        w="80px" 
        h="80px" 
        borderBottomLeftRadius="full"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <Icon as={IconComponent} color={`${color}.500`} boxSize={5} position="absolute" top="15px" right="15px" />
      </Box>
      
      <Stat>
        <StatLabel fontSize="sm" color={textColor}>{title}</StatLabel>
        <StatNumber fontSize="3xl" fontWeight="bold" mt={1}>
          {value.toLocaleString()}
        </StatNumber>
        {subtitle && <StatHelpText fontSize="xs">{subtitle}</StatHelpText>}
      </Stat>
    </Box>
  )
} 