import classNames from 'classnames';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDrop } from 'react-dnd';
import { useRecoilState } from 'recoil';
import {
  Button,
  Dimmer,
  Icon,
  Label,
  Ref,
  Segment,
  Tab,
  TransitionablePortal,
} from 'semantic-ui-react';

import { Query, QueryType, useQueryType } from '../client/queries';
import { DrawerTab, ImageSize, ItemType, QueueType } from '../misc/enums';
import t from '../misc/lang';
import { DragItemData } from '../misc/types';
import { AppState } from '../state';
import GalleryCard, {
  GalleryCardData,
  galleryCardDataFields,
} from './item/Gallery';
import { EmptySegment, Visible } from './Misc';
import { DownloadLabel, DownloadQueue } from './queue/Download';
import { MetadataLabel, MetadataQueue } from './queue/Metadata';
import ListView from './view/ListView';

export function SelectedBoard({}: {}) {
  const [items, setItems] = useState([]);

  const [{ isOver }, dropRef] = useDrop(
    () => ({
      accept: ItemType.Gallery.toString(),
      drop: (item: DragItemData, monitor) => {
        setItems([...items, item.data]);
      },
      canDrop: (item, monitor) => !items.find((v) => v.id === item.data.id),
      collect: (monitor) => ({
        isOver: !!monitor.isOver(),
        dragData: monitor.getItem() as DragItemData | null,
      }),
    }),
    [items]
  );

  return (
    <Ref innerRef={dropRef}>
      <Dimmer.Dimmable dimmed={isOver}>
        <Dimmer active={isOver}>
          <Icon size="large" name="plus" inverted />
        </Dimmer>
        {items.map((v) => (
          <GalleryCard
            draggable={false}
            key={v.id}
            data={v}
            horizontal
            size="mini"
          />
        ))}
        {!items.length && <EmptySegment />}
      </Dimmer.Dimmable>
    </Ref>
  );
}

export function QueueBoard({}: {}) {
  const [readingQueue, setReadingQueue] = useRecoilState(AppState.readingQueue);
  const [items, setItems] = useState<GalleryCardData[]>([]);
  const [loading, setLoading] = useState(false);

  const [{ isOver }, dropRef] = useDrop(
    () => ({
      accept: ItemType.Gallery.toString(),
      drop: (item: DragItemData, monitor) => {
        setReadingQueue([...readingQueue, item.data.id]);
      },
      canDrop: (item, monitor) => !items.find((v) => v.id === item.data.id),
      collect: (monitor) => ({
        isOver: !!monitor.isOver(),
        dragData: monitor.getItem() as DragItemData | null,
      }),
    }),
    [items, readingQueue]
  );

  useEffect(() => {
    const f_ids = readingQueue.filter((i) => !items.find((i2) => i2.id === i));
    if (f_ids.length) {
      setLoading(true);
      Query.get(QueryType.ITEM, {
        item_id: f_ids,
        item_type: ItemType.Gallery,
        profile_options: {
          size: ImageSize.Small,
        },
        fields: galleryCardDataFields,
      })
        .then((r) => {
          setItems([...items, ...(r.data as GalleryCardData[])]);
        })
        .finally(() => setLoading(false));
    }
  }, [readingQueue]);

  return (
    <Ref innerRef={dropRef}>
      <Dimmer.Dimmable
        dimmed={isOver}
        loading={loading}
        as={Segment}
        tertiary
        basic
        className="no-padding-segment">
        <Dimmer active={isOver}>
          <Icon size="large" name="plus" inverted />
        </Dimmer>
        <ListView
          items={items}
          className="no-margins"
          itemRender={GalleryCard}
          onItemKey={useCallback((i) => i.id, [])}
        />
        {!items.length && <EmptySegment />}
      </Dimmer.Dimmable>
    </Ref>
  );
}

export function RecentViewed() {
  const items = [];

  return <>{!items.length && <EmptySegment />}</>;
}

function DrawerPane({ children }: { children: React.ReactNode }) {
  return (
    <Tab.Pane basic className="no-padding-segment min-250-h max-250-h">
      {children}
    </Tab.Pane>
  );
}

export function Drawer({
  className,
  id,
  onClose,
}: {
  className?: string;
  id?: string;
  onClose?: () => void;
}) {
  const [drawerTab, setDrawerTab] = useRecoilState(AppState.drawerTab);

  return (
    <Segment id={id} className={classNames('no-padding-segment', className)}>
      <Tab
        activeIndex={drawerTab}
        onTabChange={useCallback((ev, d) => {
          setDrawerTab(parseInt(d.activeIndex as string, 10));
        }, [])}
        menu={useMemo(
          () => ({ pointing: true, secondary: true, size: 'small' }),
          []
        )}
        panes={useMemo(
          () => [
            {
              menuItem: {
                key: 'queue',
                content: t`Queue`,
                icon: 'book open',
              },
              render: () => (
                <DrawerPane>
                  <QueueBoard />
                </DrawerPane>
              ),
            },
            {
              menuItem: {
                key: 'metadata',
                content: (
                  <>
                    {t`Metadata`} <MetadataLabel />
                  </>
                ),
                icon: 'cloud',
              },
              render: () => (
                <DrawerPane>
                  <MetadataQueue />
                </DrawerPane>
              ),
            },
            {
              menuItem: {
                key: 'download',
                content: (
                  <>
                    {t`Download`} <DownloadLabel />
                  </>
                ),
                icon: 'download',
              },
              render: () => (
                <DrawerPane>
                  <DownloadQueue />
                </DrawerPane>
              ),
            },
            {
              menuItem: {
                key: 'selected',
                content: t`Selected`,
                icon: 'object ungroup outline icon',
              },
              render: () => (
                <DrawerPane>
                  <SelectedBoard />
                </DrawerPane>
              ),
            },

            {
              menuItem: {
                key: 'recent',
                content: t`Recently viewed`,
                icon: 'history',
              },
              render: () => (
                <DrawerPane>
                  <RecentViewed />
                </DrawerPane>
              ),
            },
          ],
          []
        )}
      />
      <Label as="a" attached="top right" onClick={onClose}>
        <Icon name="close" fitted />
      </Label>
    </Segment>
  );
}

export default function DrawerPortal({
  open,
  onClose,
}: {
  open?: boolean;
  onClose?: () => void;
}) {
  return (
    <TransitionablePortal open={open} onClose={onClose}>
      <div id="drawer">
        <Drawer onClose={onClose} />
      </div>
    </TransitionablePortal>
  );
}

export function DrawerButton({ basic }: { basic?: boolean }) {
  const [drawerTab, setDrawerTab] = useRecoilState(AppState.drawerTab);

  const [open, setOpen] = useRecoilState(AppState.drawerOpen);

  const [metadataInterval, setMetadataInterval] = useState(10000);
  const [downloadInterval, setDownloadInterval] = useState(10000);

  const { data: metadataData } = useQueryType(
    QueryType.QUEUE_STATE,
    {
      queue_type: QueueType.Metadata,
      include_finished: false,
    },
    {
      refetchInterval: metadataInterval,
    }
  );

  const { data: downloadData } = useQueryType(
    QueryType.QUEUE_STATE,
    {
      queue_type: QueueType.Download,
      include_finished: false,
    },
    {
      refetchInterval: downloadInterval,
    }
  );

  useEffect(() => {
    setMetadataInterval(
      metadataData?.data?.running && metadataData?.data?.size ? 10000 : 25000
    );
    setDownloadInterval(
      downloadData?.data?.running && downloadData?.data?.size ? 10000 : 25000
    );
  }, [metadataData, downloadData]);

  const size =
    (metadataData?.data?.size ?? 0) + (downloadData?.data?.size ?? 0);

  const labelClick = useCallback(() => {
    if (![DrawerTab.Download, DrawerTab.Metadata].includes(drawerTab)) {
      setDrawerTab(DrawerTab.Metadata);
      setTimeout(() => setOpen(true), 10);
    } else {
      setOpen(true);
    }
  }, []);

  return (
    <Visible visible={!open}>
      {!!size && (
        <Label
          as="a"
          circular
          basic
          onClick={labelClick}
          content={size}
          color={
            !metadataData?.data?.running && !downloadData?.data?.running
              ? 'red'
              : metadataData?.data?.running && downloadData?.data?.running
              ? 'green'
              : 'orange'
          }
          size="tiny"
          floating
        />
      )}
      <Button
        primary
        circular
        basic={basic}
        onClick={useCallback(() => setOpen(true), [])}
        icon="window maximize outline"
        size="small"
      />
    </Visible>
  );
}
