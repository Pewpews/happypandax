import { DragBoard } from './Drawer';
import { GalleryCard } from './Gallery';
import PageLayout from './layout/Page';

export default {
  title: 'Item/Gallery',
};

const data = (id: number, title = 'title_test', artist = 'testy') => ({
  id,
  preferred_title: { name: title },
  artists: [{ preferred_name: { name: artist } }],
});

export const Card = () => <GalleryCard data={data(1)} />;

export const Horizontal = () => (
  <GalleryCard data={data(1)} horizontal size="tiny" />
);

export const Draggable = () => (
  <PageLayout>
    <GalleryCard data={data(1)} horizontal size="tiny" />
    <GalleryCard data={data(2)} />
    <DragBoard />
  </PageLayout>
);
