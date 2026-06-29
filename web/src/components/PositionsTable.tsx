import { Wallet } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Delta } from '@/components/Delta'
import { formatUsd } from '@/lib/format'
import type { Position } from '@/lib/types'

export function PositionsTable({
  positions,
  price,
}: {
  positions: Position[]
  price?: number | null
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Posiciones abiertas</CardTitle>
        {positions.length > 0 && (
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 font-mono text-xs font-medium tabular-nums text-zinc-600">
            {positions.length}
          </span>
        )}
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Símbolo</TableHead>
              <TableHead>Lado</TableHead>
              <TableHead className="text-right">Entrada</TableHead>
              <TableHead className="text-right">Actual</TableHead>
              <TableHead className="text-right">P&L</TableHead>
              <TableHead className="text-right">Stop</TableHead>
              <TableHead className="text-right">Take</TableHead>
              <TableHead className="text-right">Valor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {positions.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={8}>
                  <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
                    <Wallet className="h-7 w-7 text-zinc-300" aria-hidden="true" />
                    <p className="text-sm font-medium text-zinc-600">Sin posiciones abiertas</p>
                    <p className="text-xs text-zinc-400">Aparecerán aquí cuando Américo entre al mercado.</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              positions.map((p) => {
                // Precio en vivo del feed; si todavía no llegó, cae a la entrada (P&L 0).
                const current = price && price > 0 ? price : p.entry_price
                const pnl = (current - p.entry_price) * p.quantity
                const value = current * p.quantity
                return (
                  <TableRow key={p.symbol}>
                    <TableCell className="font-mono font-semibold text-zinc-900">{p.symbol}</TableCell>
                    <TableCell>
                      <Badge variant="success">LARGO</Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">{formatUsd(p.entry_price)}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums">{formatUsd(current)}</TableCell>
                    <TableCell className="text-right">
                      <Delta value={pnl} label={formatUsd(pnl)} className="justify-end" />
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-zinc-500">{formatUsd(p.stop_loss)}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-zinc-500">{formatUsd(p.take_profit)}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums">{formatUsd(value)}</TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
