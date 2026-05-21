<script setup>
import { useRouter } from 'vue-router'
import Table from '@/components/ui/Table.vue'
import TableHeader from '@/components/ui/TableHeader.vue'
import TableBody from '@/components/ui/TableBody.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableHead from '@/components/ui/TableHead.vue'
import TableCell from '@/components/ui/TableCell.vue'
import Badge from '@/components/ui/Badge.vue'
import TaxonName from '@/components/common/TaxonName.vue'
import CompareToggle from '@/components/auction/CompareToggle.vue'
import { formatPrice, formatDate, xorId } from '@/lib/utils'

defineProps({ items: { type: Array, default: () => [] } })
const router = useRouter()
</script>

<template>
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead class="w-[40px]"></TableHead>
        <TableHead class="min-w-[220px]">名称 / Taxon</TableHead>
        <TableHead class="w-[120px]">科</TableHead>
        <TableHead class="w-[100px]">尺寸</TableHead>
        <TableHead class="min-w-[160px]">产地</TableHead>
        <TableHead class="w-[100px] text-right">成交价</TableHead>
        <TableHead class="w-[110px]">截拍日期</TableHead>
        <TableHead class="w-[80px]">状态</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      <TableRow
        v-for="item in items"
        :key="item.item_no"
        class="cursor-pointer"
        @click="router.push(`/auctions/${xorId(item.item_no)}`)"
      >
        <TableCell @click.stop>
          <CompareToggle :item="item" />
        </TableCell>
        <TableCell><TaxonName :name="item.name || '—'" class="text-sm" /></TableCell>
        <TableCell class="text-sm">{{ item.family || '—' }}</TableCell>
        <TableCell class="text-sm text-muted-foreground">{{ item.size || '—' }}</TableCell>
        <TableCell class="text-sm text-muted-foreground">{{ item.locality || '—' }}</TableCell>
        <TableCell class="text-right font-mono text-sm tabular-nums">{{ formatPrice(item.final_price) || '—' }}</TableCell>
        <TableCell class="text-sm text-muted-foreground">{{ formatDate(item.end_date) }}</TableCell>
        <TableCell>
          <Badge :variant="item.is_sold ? 'default' : 'muted'" class="text-[10px] uppercase tracking-wider">
            {{ item.buyer === '- no Bids' ? '流拍' : (item.is_sold ? 'Sold' : 'Unsold') }}
          </Badge>
        </TableCell>
      </TableRow>
    </TableBody>
  </Table>
</template>
