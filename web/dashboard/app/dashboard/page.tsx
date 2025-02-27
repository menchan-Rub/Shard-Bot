'use client'

import {
  Box,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Card,
  CardBody,
  Heading,
} from '@chakra-ui/react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const options = {
  responsive: true,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: true,
      text: 'Bot Usage Statistics',
    },
  },
}

const labels = ['January', 'February', 'March', 'April', 'May', 'June', 'July']
const data = {
  labels,
  datasets: [
    {
      label: 'Commands Used',
      data: [65, 59, 80, 81, 56, 55, 40],
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.5)',
    },
  ],
}

export default function DashboardPage() {
  return (
    <Box>
      <Heading mb={6}>Overview</Heading>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mb={8}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Servers</StatLabel>
              <StatNumber>100</StatNumber>
              <StatHelpText>Active Discord Servers</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Users</StatLabel>
              <StatNumber>5,000</StatNumber>
              <StatHelpText>Across all servers</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Commands Used</StatLabel>
              <StatNumber>25,000</StatNumber>
              <StatHelpText>Last 30 days</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>
      <Card>
        <CardBody>
          <Line options={options} data={data} />
        </CardBody>
      </Card>
    </Box>
  )
} 